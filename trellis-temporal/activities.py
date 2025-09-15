from __future__ import annotations
import asyncio
from typing import Dict, Any
from decimal import Decimal  # <-- add this

from temporalio import activity
import db
import stubs

@activity.defn
async def receive_order_act(order_id: str) -> Dict[str, Any]:
    order = await stubs.order_received(order_id)
    return {"order_id": order_id, "items": order.get("items", [])}

@activity.defn
async def validate_order_act(order: dict) -> Dict[str, Any]:
    valid = await stubs.order_validated(order)
    return {"order_id": order.get("order_id"), "valid": bool(valid)}

@activity.defn
async def charge_payment_act(order: dict, payment_id: str) -> dict:
    """
    Idempotent payment charge:
      - If payment_id already recorded as charged, return that.
      - Else perform charge and record it exactly once.
    """
    order_id = order.get("order_id") or ""

    # 1) try to create a payment row (idempotency key = payment_id)
    created = await db.try_create_payment(payment_id, order_id)
    if not created:
        rec = await db.get_payment(payment_id)
        amount = rec.get("amount")
        if isinstance(amount, Decimal):  # normalize Decimal
            amount = int(amount)
        return {"status": rec["status"], "amount": amount or 0}

    # 2) perform the (fake) charge
    res = await stubs.payment_charged(order, payment_id)
    amount = int(res.get("amount") or 0)

    # 3) mark charged + append event
    await db.mark_payment(payment_id, "charged", amount)
    await db.append_event(order_id, "payment_charged", {"amount": amount})

    return {"status": "charged", "amount": amount}

@activity.defn
async def prepare_package_act(order: dict) -> dict:
    res = await stubs.package_prepared(order)
    return {"status": res}

@activity.defn
async def dispatch_carrier_act(order: dict) -> dict:
    res = await stubs.carrier_dispatched(order)
    return {"status": res}
