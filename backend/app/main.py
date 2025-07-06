import os
import contextlib
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis
from psycopg_pool import AsyncConnectionPool

from backend.database import db
from backend.app.routers import users, inference, auth, payments

# Load env variables
load_dotenv()


@contextlib.asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    # On Startup
    print("Application starting up...")

    # Initialize Redis
    db.redis_client = Redis(host="localhost", port=6379, db=0, decode_responses=True)
    try:
        await db.redis_client.ping()
        print("Successfully connected to Redis.")
    except Exception as e:                                                                           # pylint: disable=broad-exception-caught
        print(f"Failed to connect to Redis: {e}")

    # Initialize PostgreSQL Connection Pool
    POSTGRES_PASSWD = os.getenv("POSTGRESS_PASSWD")                                                  # pylint: disable=invalid-name
    if not POSTGRES_PASSWD:
        raise ValueError("POSTGRESS_PASSWD environment variable not set.")

    POSTGRES_CONN_STRING = (                                                                         # pylint: disable=invalid-name
        f"postgresql://postgres:{POSTGRES_PASSWD}" "@localhost:5432/rainference"
    )
    db.psql_pool = AsyncConnectionPool(conninfo=POSTGRES_CONN_STRING, open=False)
    try:
        await db.psql_pool.open()  # Open the pool connections
        print("PostgreSQL connection pool created.")
    except Exception as e:                                                                           # pylint: disable=broad-exception-caught
        print(f"Failed to connect to PostgreSQL: {e}")

    yield  # The application runs here

    # --- On Shutdown ---
    print("Application shutting down...")
    if db.redis_client:
        await db.redis_client.close()
        print("Redis connection closed.")
    if db.psql_pool:
        await db.psql_pool.close()
        print("PostgreSQL connection pool closed.")


# Initialize FastAPI
app = FastAPI(title="FastAPI Backend", lifespan=lifespan)

# Configure CORS for frontend
origins = os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else []
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include your routers
app.include_router(users.router)
app.include_router(inference.router)
app.include_router(auth.router)
app.include_router(payments.router)


# root endpoint for health check
@app.get("/")
async def read_root():
    return {"message": "Welcome to the FastAPI backend!"}
