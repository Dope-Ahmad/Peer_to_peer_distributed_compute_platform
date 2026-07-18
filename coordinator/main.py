from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from uuid import UUID
from contextlib import asynccontextmanager
from coordinator import database
import json


@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()
    async with database.get_pool().acquire() as conn:
        version = await conn.fetchval("SELECT version();")
        print(f"Connected: {version.split(',')[0]}")
    yield
    await database.disconnect()


app = FastAPI(title= "ComputeLend Coordinator", lifespan=lifespan)

class JobSubmit(BaseModel):
    code: str
    input_data: dict = {}

    cpu_limit: float = 1.0 #Minimum CPU Core
    memory_limit_mb: int = 512 #Minimum RAM MBs

class WorkerRegister(BaseModel):
    hostname: str
    ip_address: str
    port: int
    cpu_cores: int
    memory_limit: int

@app.get("/")
def root():
    return {"status": "coordinator running"}
@app.post("/jobs/submit", status_code=201)
async def submit_job(job: JobSubmit):
    async with database.get_pool().acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO jobs (code, input_data,cpu_limit,memory_limit_mb)
            VALUES ($1, $2::jsonb, $3, $4)
            RETURNING id, status, submitted_at
            """,
            job.code,
            json.dumps(job.input_data),
            job.cpu_limit,
            job.memory_limit_mb,
        )
        return {
        "job_id": str(row["id"]),
        "status": row["status"],
        "submitted_at": row["submitted_at"],
        }

@app.get("/jobs/{job_id}/status")
async def get_job_status(job_id: UUID):
    async with database.get_pool().acquire() as conn:
        row = await conn.fetchrow(
        """
        SELECT id, status, worker_id, retry_count, submitted_at, started_at, completed_at
        FROM jobs
        WHERE id = $1
        """,
        job_id
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Job not found")

        return dict(row)


@app.post("/workers/register", status_code=201)
async def register_worker(worker: WorkerRegister):
    async with database.get_pool().acquire() as conn:
        row = await conn.fetchrow(
        """
        INSERT INTO workers (hostname, ip_address, port, cpu_cores, memory_mb)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, status, registered_at
        """,
            worker.hostname,
            worker.ip_address,
            worker.port,
            worker.cpu_cores,
            worker.memory_limit,
        )
        return{"worker_id": str(row["id"]),
        "status": row["status"],
        "registered_at": row["registered_at"]}




