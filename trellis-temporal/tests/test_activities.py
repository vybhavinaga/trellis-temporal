import uuid, os, importlib, pytest
os.environ["TRELLIS_DEMO_OK"] = "1"
import stubs; importlib.reload(stubs)
import activities

@pytest.mark.asyncio
async def test_charge_payment_act_is_idempotent_and_json_safe():
    pid = f"pay-{uuid.uuid4().hex[:8]}"
    order = {"order_id": f"o-{uuid.uuid4().hex[:8]}", "items": [{"sku":"A","qty":2}]}
    out1 = await activities.charge_payment_act(order, pid)
    assert out1["status"] == "charged"
    assert int(out1["amount"]) == 2
    out2 = await activities.charge_payment_act(order, pid)
    assert out2["status"] == "charged"
    assert int(out2["amount"]) == 2
