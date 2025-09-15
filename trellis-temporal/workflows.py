# workflows.py
from __future__ import annotations
from datetime import timedelta
from typing import Any, Dict, Optional

from temporalio import workflow
from temporalio.common import RetryPolicy

from config import TASK_QUEUE_ORDERS, TASK_QUEUE_SHIPPING
from activities import (
    receive_order_act,
    validate_order_act,
    charge_payment_act,
    prepare_package_act,
    dispatch_carrier_act,
)

ACT_TIMEOUT = timedelta(seconds=1)
RETRY = RetryPolicy(
    initial_interval=timedelta(milliseconds=500),
    backoff_coefficient=1.5,
    maximum_attempts=2,
    maximum_interval=timedelta(seconds=5),
)

@workflow.defn
class ShippingWorkflow:
    @workflow.run
    async def run(self, order: Dict[str, Any]) -> str:
        try:
            await workflow.execute_activity(
                prepare_package_act, args=[order],
                start_to_close_timeout=ACT_TIMEOUT, retry_policy=RETRY
            )
            await workflow.execute_activity(
                dispatch_carrier_act, args=[order],
                start_to_close_timeout=ACT_TIMEOUT, retry_policy=RETRY
            )
            return "ok"
        except Exception as e:
            parent_id = workflow.info().parent_workflow_id
            if parent_id:
                await workflow.signal_external_workflow(
                    parent_id, "dispatch_failed", args=[str(e)]
                )
            raise

@workflow.defn
class OrderWorkflow:
    def __init__(self) -> None:
        self._approved: bool = False
        self._canceled: bool = False
        self._dispatch_fail_reason: Optional[str] = None
        self._step: str = "init"
        self._address: Dict[str, Any] = {}

    @workflow.signal
    async def approve(self) -> None:
        self._approved = True

    @workflow.signal
    async def cancel(self) -> None:
        self._canceled = True

    @workflow.signal
    async def update_address(self, address: Dict[str, Any]) -> None:
        if isinstance(address, dict):
            self._address.update(address)

    @workflow.signal
    async def dispatch_failed(self, reason: str) -> None:
        self._dispatch_fail_reason = reason

    @workflow.query
    def status(self) -> Dict[str, Any]:
        return {
            "approved": self._approved,
            "canceled": self._canceled,
            "step": self._step,
            "address": self._address,
        }

    @workflow.run
    async def run(self, order_id: str, payment_id: str, address: Dict[str, Any]) -> str:
        self._address = dict(address or {})

        self._step = "receive"
        order = await workflow.execute_activity(
            receive_order_act, args=[order_id],
            start_to_close_timeout=ACT_TIMEOUT, retry_policy=RETRY
        )
        order = {**order, "address": self._address}

        self._step = "validate"
        await workflow.execute_activity(
            validate_order_act, args=[order],
            start_to_close_timeout=ACT_TIMEOUT, retry_policy=RETRY
        )

        self._step = "manual_review"
        # open-ended deterministic wait (overall 15s run_timeout still applies)
        await workflow.wait_condition(lambda: self._approved or self._canceled)
        if self._canceled:
            raise RuntimeError("Canceled in review")

        self._step = "charge"
        order = {**order, "address": self._address}
        await workflow.execute_activity(
            charge_payment_act, args=[order, payment_id],
            start_to_close_timeout=ACT_TIMEOUT, retry_policy=RETRY
        )

        self._step = "ship"
        attempt = 0
        while True:
            child_id = f"ship-{order_id}-{workflow.info().run_id[:6]}"
            try:
                await workflow.execute_child_workflow(
                    ShippingWorkflow.run,
                    args=[{**order, "address": self._address}],
                    id=child_id,
                    task_queue=TASK_QUEUE_SHIPPING,
                    retry_policy=RETRY,
                )
                break
            except Exception:
                if self._dispatch_fail_reason and attempt == 0:
                    self._dispatch_fail_reason = None
                    attempt += 1
                    continue
                raise

        self._step = "done"
        return "done"
