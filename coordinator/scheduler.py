import asyncio
import logging

import httpx

from coordinator.database import get_pool
import json

logger = logging.getLogger(__name__)

SLEEP_TIME = 2

async def run_scheduler():
    logger.info("Starting scheduler...")
    while True:
        try:
            job_dispatched = await _schedule_pending_job()
        except Exception as e:
            logger.error(f"Scheduler Error: {e}")
            job_dispatched = 0
        if job_dispatched == 0:
            await asyncio.sleep(SLEEP_TIME)

async def _schedule_pending_job():
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            job = await conn.fetchrow(
            """
            SELECT id, cpu_limit, memory_limit_mb, code, timeout_secs
            FROM jobs
            WHERE status = 'queued'
            ORDER BY priority ASC, submitted_at ASC
            LIMIT 1
            FOR UPDATE SKIP LOCKED
            """
            )
            if job is None:
                return 0

            worker = await conn.fetchrow(
            """
            SELECT id, hostname, ip_address, port
            FROM workers
            WHERE status = 'idle'
                AND cpu_cores >= $1
                AND memory_mb >= $2
            ORDER BY last_seen DESC
            LIMIT 1
            FOR UPDATE SKIP LOCKED
            """,
                job['cpu_limit'],
                job['memory_limit_mb'],
            )
            if worker is None:
                return 0
            await conn.execute(
                """
                UPDATE jobs
                SET status = 'dispatched',
                    worker_id = $1
                WHERE id = $2
                """,
                worker['id'],
                job['id'],
            )
            await conn.execute(
            """
            UPDATE workers
            SET status = 'busy'
            WHERE id = $1
            """,
                worker['id']
            )
    await _dispatch_to_worker(job, worker)
    return 1

async def _dispatch_to_worker(job, worker):
    url = "https://"+worker['ip_address']+":"+worker['port']+"/execute"
    payload = {
        "job_id": str(job['id']),
        "code": job['code'],
        "input_data": json.loads(job['input_data']),
        "cpu_limit": job['cpu_limit'],
        "memory_limit_mb": job['memory_limit_mb'],
        "timeout_secs": job['timeout_secs'],
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
    except httpx.HTTPError as e:


