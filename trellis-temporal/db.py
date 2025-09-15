from __future__ import annotations
import asyncpg
import json
from typing import Any, Dict, Optional
from decimal import Decimal  # <-- added
from config import DATABASE_URL

_pool: Optional[asyncpg.Pool] = None

async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=4)
    return _pool

# ----- payments (idempotency by payment_id) -----
async def try_create_payment(payment_id: str, order_id: str) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO payments (payment_id, order_id, status)
            VALUES ($1, $2, 'created')
            ON CONFLICT (payment_id) DO NOTHING
            RETURNING payment_id
            """,
            payment_id, order_id,
        )
        return bool(row)

async def get_payment(payment_id: str) -> Dict[str, Any]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT payment_id, order_id, status, amount FROM payments WHERE payment_id=$1",
            payment_id,
        )
        if not row:
            return {}
        result = dict(row)
        # Convert Decimal → int (or float) so JSON can serialize
        if isinstance(result.get("amount"), Decimal):
            result["amount"] = int(result["amount"])
        return result

async def mark_payment(payment_id: str, status: str, amount: int | None) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE payments SET status=$2, amount=$3 WHERE payment_id=$1",
            payment_id, status, amount,
        )

# ----- events (optional audit) -----
async def append_event(order_id: str, event_type: str, payload: Dict[str, Any]) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Wrap in a transaction so the protocol state is clean on release
        async with conn.transaction():
            await conn.execute(
                "INSERT INTO events (order_id, type, payload_json) VALUES ($1, $2, $3::jsonb)",
                order_id, event_type, json.dumps(payload or {}),
            )


# --- test/teardown helper ---
async def close_pool() -> None:
    global _pool
    pool, _pool = _pool, None
    if pool is not None:
        await pool.close()

