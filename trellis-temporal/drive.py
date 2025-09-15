# drive.py
import asyncio
import os
import random
import string
from datetime import timedelta

from temporalio.client import Client
from workflows import OrderWorkflow
from config import TASK_QUEUE_ORDERS  # must match your worker's orders queue


def _rid(n: int = 6) -> str:
    """Random short id."""
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789"
    return "".join(random.choices(alphabet, k=n))


async def main() -> None:
    # This only affects the *current* process. Ensure you also export this
    # in the worker terminal so the activities/stubs use demo mode too.
    os.environ.setdefault("TRELLIS_DEMO_OK", "1")

    client = await Client.connect("localhost:7233")

    order_key = f"o-{_rid()}"
    payment_id = f"p-{_rid()}"
    workflow_id = f"order-{order_key}"
    print("Starting:", workflow_id, payment_id)

    # Start the workflow on the same task queue your worker polls.
    h = await client.start_workflow(
        OrderWorkflow.run,                     # entrypoint
        id=workflow_id,                        # e.g. order-o-abc123
        task_queue=TASK_QUEUE_ORDERS,          # from config.py
        args=[order_key, payment_id, {"city": "Amherst"}],
        run_timeout=timedelta(seconds=15),
        rpc_timeout=timedelta(seconds=30),
    )
    print("Started", h.id)

    # Give the worker a moment to reach manual_review; then approve.
    await asyncio.sleep(1.0)
    await h.signal("approve")                  # signal via handle (SDK-safe)
    print("Approved")

    # Don’t use queries (they can RPC-timeout if no poller). Just wait
    # for the workflow result with a generous client RPC timeout.
    result = await h.result(rpc_timeout=timedelta(seconds=60))
    print("✅ Completed with result:", result)


if __name__ == "__main__":
    asyncio.run(main())
