import pytest
from coordinator import database
from coordinator.scheduler import _schedule_pending_job
from coordinator.fault_detector import _check_for_dead_workers

pytestmark = pytest.mark.asyncio


async def test_higher_priority_job_dispatched_first(clean_db):
    await clean_db.execute("INSERT INTO jobs (code, priority) VALUES ('low',7), ('high', 2)")
    await clean_db.execute("""
    INSERT INTO workers (hostname, ip_address, port, cpu_cores, memory_mb) VALUES ('w1', '127.0.0.1', 8001, 4, 8192)
    """)

    dispatched = await _schedule_pending_job()
    assert dispatched == 1
    row = await clean_db.fetchrow("SELECT code, priority FROM jobs WHERE status = 'dispatched'")
    assert row['code'] == 'high'
    assert row['priority'] == 2

async def test_job_not_dispatched_to_undersized_worker(clean_db):
    await clean_db.execute(
        "INSERT INTO jobs (code, cpu_limit, memory_limit_mb) VALUES ('big', 8.0, 65536)"
    )
    await clean_db.execute(
        """
        INSERT INTO workers (hostname, ip_address, port, cpu_cores, memory_mb)
        VALUES ('small', '127.0.0.1', 8001, 2, 4096)
        """
    )

    dispatched = await _schedule_pending_job()

    assert dispatched == 0
    status = await clean_db.fetchval("SELECT status FROM jobs")
    assert status == "queued"

async def test_empty_queue_is_noop(clean_db):
    dispatched = await _schedule_pending_job()
    assert dispatched == 0

async def test_dead_worker_job_is_requeued(clean_db):
    worker_id = await clean_db.fetchval(
        """
        INSERT INTO workers (hostname, ip_address, port, cpu_cores, memory_mb, status, last_seen)
        VALUES ('zombie', '127.0.0.1', 8001, 4, 8192, 'busy', NOW() - INTERVAL '60 seconds')
        RETURNING id
        """
    )
    await clean_db.execute(
        "INSERT INTO jobs (code, status, worker_id) VALUES ('orphan', 'running', $1)",
        worker_id,
    )

    await _check_for_dead_workers()

    job = await clean_db.fetchrow("SELECT status, worker_id, retry_count FROM jobs")
    assert job["status"] == "queued"
    assert job["worker_id"] is None
    assert job["retry_count"] == 1

    worker_status = await clean_db.fetchval("SELECT status FROM workers")
    assert worker_status == "offline"

async def test_job_fails_when_retries_exhausted(clean_db):
    worker_id = await clean_db.fetchval(
        """
        INSERT INTO workers (hostname, ip_address, port, cpu_cores, memory_mb, status, last_seen)
        VALUES ('zombie', '127.0.0.1', 8001, 4, 8192, 'busy', NOW() - INTERVAL '60 seconds')
        RETURNING id
        """
    )
    await clean_db.execute(
        """
        INSERT INTO jobs (code, status, worker_id, retry_count, max_retries)
        VALUES ('doomed', 'running', $1, 2, 2)
        """,
        worker_id,
    )

    await _check_for_dead_workers()

    status = await clean_db.fetchval("SELECT status FROM jobs")
    assert status == "failed"