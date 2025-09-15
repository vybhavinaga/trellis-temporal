from __future__ import annotations
import os, asyncio, random
from typing import Dict, Any

# Set TRELLIS_DEMO_OK=1 to disable flakiness locally
DEMO_OK = os.getenv("TRELLIS_DEMO_OK", "0") == "1"

async def flaky_call() -> None:
    if DEMO_OK:
        return
    r = random.random()
    if r < 0.33:
        raise RuntimeError("Forced failure for testing")
    if r < 0.67:
        await asyncio.sleep(300)  # long sleep to trigger activity timeout

async def order_received(order_id: str) -> Dict[str, Any]:
    await flaky_call()
    return {"order_id": order_id, "items": [{"sku": "ABC", "qty": 1}]}

async def order_validated(order: Dict[str, Any]) -> bool:
    await flaky_call()
    if not order.get("items"):
        raise ValueError("No items to validate")
    return True

async def payment_charged(order: Dict[str, Any], payment_id: str) -> Dict[str, Any]:
    await flaky_call()
    amount = sum(i.get("qty", 1) for i in order.get("items", []))
    return {"status": "charged", "amount": amount}

async def package_prepared(order: Dict[str, Any]) -> str:
    await flaky_call()
    return "Package ready"

async def carrier_dispatched(order: Dict[str, Any]) -> str:
    await flaky_call()
    return "Dispatched"
