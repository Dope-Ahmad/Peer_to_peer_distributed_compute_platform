from fastapi import FastAPI
from pydantic import BaseModel
import uuid
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



