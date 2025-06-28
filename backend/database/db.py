import os
from redis.asyncio import Redis
from psycopg_pool import AsyncConnectionPool
from typing import AsyncGenerator

# --- Placeholders for our connections ---
# They are initialized in the lifespan event in main.py
redis_client: Redis | None = None
psql_pool: AsyncConnectionPool | None = None

# --- Dependency for Redis ---
async def get_redis_client() -> Redis:
    if redis_client is None:
        raise RuntimeError("Redis client not initialized")
    return redis_client

# --- Dependency for PostgreSQL ---
async def get_psql_conn() -> AsyncGenerator:
    """
    Dependency function that yields a connection from the pool.
    This ensures the connection is returned to the pool after the request is finished.
    """
    if psql_pool is None:
        raise RuntimeError("PostgreSQL connection pool not initialized")
    
    # The 'async with' statement handles acquiring a connection from the pool
    # and releasing it back to the pool when the block is exited.
    async with psql_pool.connection() as conn:
        yield conn
