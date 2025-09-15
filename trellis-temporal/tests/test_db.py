import uuid, pytest, db
@pytest.mark.asyncio
async def test_payment_idempotency_roundtrip():
    pid = f"test-{uuid.uuid4().hex[:8]}"
    oid = f"o-{uuid.uuid4().hex[:8]}"
    assert await db.try_create_payment(pid, oid) is True
    assert await db.try_create_payment(pid, oid) is False
    await db.mark_payment(pid, "charged", 7)
    rec = await db.get_payment(pid)
    assert rec["payment_id"] == pid
    assert rec["status"] == "charged"
    assert int(rec["amount"]) == 7

@pytest.mark.asyncio
async def test_append_event_inserts():
    oid = f"o-{uuid.uuid4().hex[:8]}"
    await db.append_event(oid, "unit_test_event", {"k":"v"})
