import pytest
import pytest_asyncio
from coordinator.main import app
from httpx import AsyncClient, ASGITransport

pytestmark = pytest.mark.asyncio

async def _client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url='http://test')

async def test_submit_job_201_persists(clean_db):
    async with await _client() as client:
        response = await client.post("/jobs/submit",
                                     json={"code":"print('Hello World')",
                                           "input_data": {"go":1}})
        assert response.status_code == 201
        body = response.json()
        assert "job_id" in body
        assert body["status"] == 'queued'

        row = await clean_db.fetchrow(
        """
        SELECT code, status FROM jobs WHERE id = $1
        """, __import__('uuid').UUID(body['job_id'])
        )
        assert row is not None
        assert row['status'] == 'queued'

async def test_get_status_unknown_job_returns_404(clean_db):
    async with await _client() as client:
        response = await client.get("/jobs/00000000-0000-0000-0000-000000000000/status")
    assert response.status_code == 404

async def test_get_status_malformed_uuid_returns_422(clean_db):
    async with await _client() as client:
        response = await client.get("/jobs/not-a-uuid/status")
    assert response.status_code == 422

async def test_register_worker_persists(clean_db):
    async with await _client() as client:
        response = await client.post(
            "/workers/register",
            json={
                "hostname": "test-box",
                "ip_address": "127.0.0.1",
                "port": 8001,
                "cpu_cores": 4,
                "memory_limit": 8192,
            },
        )

    assert response.status_code == 201
    count = await clean_db.fetchval("SELECT COUNT(*) FROM workers")
    assert count == 1
