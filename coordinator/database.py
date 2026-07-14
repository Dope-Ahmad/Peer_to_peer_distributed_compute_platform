import asyncpg

DATABASE_URL = "postgresql://computelend:localdevpassword@localhost:5432/computelend"

pool: asyncpg.Pool | None = None

async def connect():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL,
                                     min_size=2,
                                     max_size=10)
async def disconnect():
    if pool:
        await pool.close()

def get_pool() -> asyncpg.Pool:
    if pool is None:
        raise RuntimeError("Databse pool is not initialized")
    return pool


