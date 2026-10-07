import asyncio
import logging
from contextlib import asynccontextmanager
import httpx
import psutil
from worker import config
from fastapi import FastAPI
from pydantic import BaseModel

logger = logging.getLogger(__name__)

worker_id: str | None = None

async def register_with_coordinator() -> str:

    cpu_cores = psutil.cpu_count(logical=True)
    memory_mb = int(psutil.virtual_memory().total / (1024 * 1024))

    body = {"hostname": ("worker-" + str(config.WORKER_PORT)),
            "ip_address": str(config.WORKER_HOST),
            "port": config.WORKER_PORT,
            "cpu_cores": cpu_cores,
            "memory_limit": memory_mb}

    while True:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:

                endpoint = str(config.COORDINATOR_URL) + "/workers/register"
                response = await client.post(endpoint, json=body,)
                response.raise_for_status()
                worker_id = response.json().get("worker_id")
                logger.info(f"Register as {worker_id}" f"({cpu_cores} cores, {memory_mb} MB)")
                return worker_id
        except httpx.HTTPError as err:
            logger.warning(f"Registration failed ({err}); retrying in 5s")
            await asyncio.sleep(5)

async def heartbeat_loop():
    logger.info("Starting heartbeat loop")
    async with httpx.AsyncClient(timeout=5) as client:
        while True:
            try:
                response = await client.post(f"{config.COORDINATOR_URL}/workers/{worker_id}/heartbeat")
                response.raise_for_status()
            except httpx.HTTPError as err:
                logger.warning(f"Heartbeat failed ({err}); retrying in 5s")
            await asyncio.sleep(config.HEARBEAT_INTERVAL)
@asynccontextmanager
async def lifespan(app: FastAPI):
    global worker_id
    worker_id = await register_with_coordinator()
    hb_task = asyncio.create_task(heartbeat_loop())
    yield
    hb_task.cancel()
    try:
        await hb_task
    except asyncio.CancelledError:
        pass

app = FastAPI(title="ComputeLend Worker", lifespan=lifespan)

class JobPayload(BaseModel):
    job_id: str
    code: str
    input_data = {}
    cpu_limit = 1.0
    memory_limit_mb = 512
    timeout_secs = 300

@app.post("/execute", status_code=202)
async def execute_job(payload: JobPayload):
    logger.info("Got the job:" + str(payload.job_id))
    asyncio.create_task(_run_job(payload))
    return {"accepted": True, "job_id": payload.job_id}

async def _run_job(payload: JobPayload):
    logger.info(f"Executing job: {payload.job_id}")
    await asyncio.sleep(1)
    logger.info(f"Finished job: {payload.job_id}")

@app.get("/health")
async def get_health():
    return {"status":"good", "worker_id": worker_id}