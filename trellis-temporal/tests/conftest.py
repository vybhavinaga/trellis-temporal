import os, sys
import pytest_asyncio

# Make repo root importable (db.py, activities.py, etc.)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Make stubs non-flaky during tests
os.environ.setdefault("TRELLIS_DEMO_OK", "1")

# Reset asyncpg pool before/after each test so it's created on the current loop
@pytest_asyncio.fixture(autouse=True)
async def reset_db_pool():
    import db
    await db.close_pool()   # ensure no leftover pool from previous test
    yield
    await db.close_pool()   # cleanly close before next test/loop
