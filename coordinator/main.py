from fastapi import FastAPI
from pydantic import BaseModel
import uuid

app = FastAPI(title= "ComputeLend Coordinator")

class JobSubmit(BaseModel):
    code: str
    input_data: dict = {}

    cpu_limit: float = 1.0 #Minimum CPU Core
    memory_limit_mb: int = 512 #Minimum RAM MBs

@app.get("/")
def root():
    return {"status": "coordinator running"}
@app.post("/jobs/submit")
def submit_job(job: JobSubmit):
    job_id = str(uuid.uuid4())
    return {"job_id": job_id,
            "status": "queued",
            "received_code_length": len(job.code)}



