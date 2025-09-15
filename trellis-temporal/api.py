from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from temporalio.client import Client
from temporalio import service as temporal_service

from config import TASK_QUEUE_ORDERS
from workflows import OrderWorkflow

app = FastAPI()
_client: Client | None = None

class StartBody(BaseModel):
    payment_id: str
    address: Dict[str, Any]

class AddressBody(BaseModel):
    address: Dict[str, Any]

async def get_client() -> Client:
    global _client
    if _client is None:
        _client = await Client.connect("localhost:7233")
    return _client

@app.get("/health")
async def health():
    try:
        await get_client()
        return {"ok": True}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": repr(e)})

@app.post("/orders/{order_id}/start")
async def start(order_id: str, body: StartBody):
    try:
        client = await get_client()
        h = await client.start_workflow(
            OrderWorkflow.run,
            id=f"order-{order_id}",
            task_queue=TASK_QUEUE_ORDERS,
            args=[order_id, body.payment_id, body.address],
            run_timeout=timedelta(seconds=15),
            rpc_timeout=timedelta(seconds=30),
        )
        return {"workflow_id": h.id}
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": repr(e)})

@app.post("/orders/{order_id}/signals/approve")
async def approve(order_id: str):
    try:
        client = await get_client()
        wf_id = f"order-{order_id}"
        h = client.get_workflow_handle(wf_id)
        try:
            await h.signal("approve")
            return {"ok": True, "path": "signal"}
        except temporal_service.RPCError as e:
            if getattr(e, "status", None) != temporal_service.RPCStatusCode.NOT_FOUND:
                return JSONResponse(status_code=400, content={"error": str(e)})
        try:
            await client.start_workflow(
                OrderWorkflow.run,
                id=wf_id,
                task_queue=TASK_QUEUE_ORDERS,
                args=[order_id, "__approve_only__", {}],
                run_timeout=timedelta(seconds=15),
                rpc_timeout=timedelta(seconds=30),
            )
        except temporal_service.RPCError as se:
            if getattr(se, "status", None) != temporal_service.RPCStatusCode.ALREADY_EXISTS:
                return JSONResponse(status_code=400, content={"error": str(se)})
        for attempt in range(18):
            try:
                await h.signal("approve")
                return {"ok": True, "path": "start_then_signal", "attempt": attempt + 1}
            except temporal_service.RPCError as e2:
                if getattr(e2, "status", None) == temporal_service.RPCStatusCode.NOT_FOUND:
                    await asyncio.sleep(0.2); continue
                return JSONResponse(status_code=400, content={"error": str(e2)})
        return JSONResponse(status_code=409, content={"error": "workflow not found after retries"})
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": repr(e)})

@app.post("/orders/{order_id}/signals/cancel")
async def cancel(order_id: str):
    try:
        client = await get_client()
        h = client.get_workflow_handle(f"order-{order_id}")
        for attempt in range(18):
            try:
                await h.signal("cancel")
                return {"ok": True, "attempt": attempt + 1}
            except temporal_service.RPCError as e:
                if getattr(e, "status", None) == temporal_service.RPCStatusCode.NOT_FOUND:
                    await asyncio.sleep(0.2); continue
                return JSONResponse(status_code=400, content={"error": str(e)})
        return JSONResponse(status_code=409, content={"error": "workflow not found"})
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": repr(e)})

@app.post("/orders/{order_id}/signals/update_address")
async def update_address(order_id: str, body: AddressBody):
    try:
        client = await get_client()
        wf_id = f"order-{order_id}"
        h = client.get_workflow_handle(wf_id)
        try:
            await h.signal("update_address", body.address)
            return {"ok": True, "path": "signal"}
        except temporal_service.RPCError as e:
            if getattr(e, "status", None) != temporal_service.RPCStatusCode.NOT_FOUND:
                return JSONResponse(status_code=400, content={"error": str(e)})
        try:
            await client.start_workflow(
                OrderWorkflow.run,
                id=wf_id,
                task_queue=TASK_QUEUE_ORDERS,
                args=[order_id, "__update_only__", body.address],
                run_timeout=timedelta(seconds=15),
                rpc_timeout=timedelta(seconds=30),
            )
        except temporal_service.RPCError as se:
            if getattr(se, "status", None) != temporal_service.RPCStatusCode.ALREADY_EXISTS:
                return JSONResponse(status_code=400, content={"error": str(se)})
        for attempt in range(18):
            try:
                await h.signal("update_address", body.address)
                return {"ok": True, "path": "start_then_signal", "attempt": attempt + 1}
            except temporal_service.RPCError as e2:
                if getattr(e2, "status", None) == temporal_service.RPCStatusCode.NOT_FOUND:
                    await asyncio.sleep(0.2); continue
                return JSONResponse(status_code=400, content={"error": str(e2)})
        return JSONResponse(status_code=409, content={"error": "workflow not found after retries"})
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": repr(e)})

@app.get("/orders/{order_id}/status")
async def status(order_id: str):
    try:
        client = await get_client()
        h = client.get_workflow_handle(f"order-{order_id}")
        state = await h.query("status", rpc_timeout=timedelta(seconds=20))
        return state
    except Exception as e:
        msg = repr(e)
        if "NOT_FOUND" in msg or "not found" in msg.lower():
            return JSONResponse(status_code=404, content={"error": "workflow not found"})
        return JSONResponse(status_code=400, content={"error": msg})

@app.post("/demo/run")
async def run_demo():
    try:
        client = await get_client()
        order_id = "demo-"
        h = await client.start_workflow(
            OrderWorkflow.run,
            id=f"order-{order_id}",
            task_queue=TASK_QUEUE_ORDERS,
            args=[order_id, "pay-demo", {"city": "Amherst"}],
            run_timeout=timedelta(seconds=15),
            rpc_timeout=timedelta(seconds=30),
        )
        await asyncio.sleep(1.0)
        await h.signal("approve")
        result = await h.result(rpc_timeout=timedelta(seconds=60))
        return {"workflow_id": h.id, "result": result}
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": repr(e)})

   
