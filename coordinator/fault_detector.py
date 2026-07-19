import asyncio
import logging
from coordinator.database import get_pool


logger = logging.getLogger(__name__)

HEARTBEAT_INTERVAL = 30
CHECK_INTERVAL_SEC = 10

async def run_fault_detector():
    logger.info("Starting fault detector")
    while True:
        try:
            await _check_for_dead_workers()
        except Exception as e:
            logger.error(f"Fault detector error: {e}")
            await asyncio.sleep(CHECK_INTERVAL_SEC)

async def _check_for_dead_workers():
    pool = get_pool()
    async with pool.acquire() as conn:
        dead_workers = await conn.fetch(
        """
        UPDATE workers
        SET status = 'offline'
        WHERE status != 'offline' AND last_seen < NOW() - INTERVAL '{timeout} seconds'
        RETURNING id, hostname
        """.format(timeout=HEARTBEAT_INTERVAL)
        )
        if not dead_workers:
            return

        for worker in dead_workers:
            logger.warning(
            f"Worker {worker['hostname']} ({worker['id']}) "
            f"marked offline - no heartbeat in {HEARTBEAT_INTERVAL} seconds)"
            )
        dead_workers_ids = [w['id'] for w in dead_workers]

        requeue = await conn.fetch(
        """
        UPDATE jobs
        SET status = 'queued', worker_id = NULL, retry_count = retry_count + 1
        WHERE worker_id = ANY($1::uuid[]) 
            AND status IN ('dispatched', 'running') 
            AND retry_count < max_retries
        RETURNING id
        """, dead_workers_ids,
        )

        await conn.execute(
        """
        UPDATE jobs
        SET status = 'failed'
        WHERE worker_id = ANY($1::uuid[])
            AND status IN ('dispatched', 'running')
            AND retry_count >= max_retries
        """, dead_workers_ids,
        )

        if requeue:
            logger.info(f"Requeued {len(requeue)} jobs from dead workers")
