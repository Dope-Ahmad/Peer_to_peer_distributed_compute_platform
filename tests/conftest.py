import asyncpg
import pytest
import pytest_asyncio
import asyncio
from coordinator import database

TEST_DATABASE_URL = "postgresql://computelend:localdevpassword@localhost:5432/computelend_test"

@pytest_asyncio.fixture()
async def test_pool():
    pool = await asyncpg.create_pool(TEST_DATABASE_URL, min_size=1, max_size=5)
    yield pool
    await pool.close()

@pytest_asyncio.fixture(autouse=True)
async def _point_coordinator_at_test_db(test_pool):
    database.pool = test_pool
    yield
    database.pool = None

@pytest_asyncio.fixture()
async def clean_db(test_pool):
    async with test_pool.acquire() as conn:
        await conn.execute("TRUNCATE jobs, workers CASCADE")
        yield conn