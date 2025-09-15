from __future__ import annotations
import asyncio, os
from temporalio.client import Client
from temporalio.worker import Worker

from config import TASK_QUEUE_ORDERS, TASK_QUEUE_SHIPPING, DATABASE_URL
from workflows import OrderWorkflow, ShippingWorkflow
from activities import (
    receive_order_act,
    validate_order_act,
    charge_payment_act,
    prepare_package_act,
    dispatch_carrier_act,
)

async def main():
    print(f"[worker] DATABASE_URL = {DATABASE_URL}", flush=True)

    client = await Client.connect("localhost:7233")

    # Orders worker: parent workflow + its activities
    orders_worker = Worker(
        client,
        task_queue=TASK_QUEUE_ORDERS,
        workflows=[OrderWorkflow],
        activities=[receive_order_act, validate_order_act, charge_payment_act],
    )

    # Shipping worker: child workflow + its activities
    shipping_worker = Worker(
        client,
        task_queue=TASK_QUEUE_SHIPPING,
        workflows=[ShippingWorkflow],
        activities=[prepare_package_act, dispatch_carrier_act],
    )

    print(f"[worker] polling queues: {TASK_QUEUE_ORDERS} and {TASK_QUEUE_SHIPPING}", flush=True)
    await asyncio.gather(orders_worker.run(), shipping_worker.run())

if __name__ == "__main__":
    asyncio.run(main())
