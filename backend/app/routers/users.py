from fastapi import APIRouter, Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi import Header, Request, HTTPException
from fastapi.responses import HTMLResponse ,JSONResponse
from redis.asyncio import Redis
from redis.exceptions import RedisError
import logging
import psycopg2
from psycopg import AsyncConnection

from database.db import get_redis_client, get_psql_conn

router = APIRouter()

# Security scheme
security = HTTPBearer()

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,  # Log level: DEBUG to capture all logs, including errors
    format="%(asctime)s - %(levelname)s - %(message)s",  # Log format
)

logger = logging.getLogger(__name__)


@router.get("/users/info")
async def get_info(authorization: str = Header(None), redis: Redis = Depends(get_redis_client),
                   conn: AsyncConnection = Depends(get_psql_conn)):

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid or missing authorization token")
    
    bearer_token = authorization.split(" ")[1]  # Extract the token

    # get the user_id form redis
    user_id = await redis.get(f"bearer_token:{bearer_token}")
    if not user_id:
        raise HTTPException(status_code=400, detail="User not found for the given token")

    try:
        # get the user data from psql
        async with conn.cursor() as cursor:
            query = '''
            SELECT user_id, user_name, llm_api_token, bearer_token, fname, lname, email, balance
            FROM users WHERE user_id = %s
            '''
            await cursor.execute(query, (user_id,))
            user_data = await cursor.fetchone()

        if not user_id:
            return {"error":"user data not found"}

        # parse the data 
        parsed_data = {
            "user_id": user_data[0],
            "user_name": user_data[1],
            "llm_api_token": user_data[2],
            "bearer_token": user_data[3],
            "fname": user_data[4],
            "lname": user_data[5],
            "email": user_data[6],
            "balance": float(user_data[7]),
        }

        return parsed_data
    
    except psycopg2.Error as e:
        logger.error(f"Database error while fetching user info: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.exception(f"Unexpected error while fetching user info: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")





# Get API keys for the current user
@router.get("/users/api-keys")
async def get_api_keys(credentials: HTTPAuthorizationCredentials = Depends(security),
    redis: Redis = Depends(get_redis_client), conn: AsyncConnection = Depends(get_psql_conn)):
    try:
        current_token = credentials.credentials

        # Check if the Bearer token exists in Redis and retrieve the corresponding user ID
        user_id = await redis.get(f"bearer_token:{current_token}")

        if not user_id:
            raise HTTPException(status_code=400, detail="Invalid Bearer token")

        # Retrieve user data from psql
        async with conn.cursor() as cursor:
            # Define the query to fetch the llm_api_token for a given user_id
                query = """
                SELECT llm_api_token,fname, user_name
                FROM users
                WHERE user_id = %s
                """
                await cursor.execute(query, (user_id,))  # Execute the query with the user_id parameter

                # Fetch the result
                result = await cursor.fetchone()

                if result:
                    return {
                        "api_token": result[0],  # llm_api_token
                        "fname": result[1],      # fname
                        "user_name": result[2],  # user_name
                    }
                else:
                    raise HTTPException(status_code=404, detail="No API token found for the user")
                
    except psycopg2.Error as db_err:
        logger.exception(f"Database error occurred while regenerating API token: {str(db_err)}")
        return "Database error", None
    
    except Exception as e:
        logger.exception(f"Error occurred while fetching API keys: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")







@router.get("/balance")
async def get_balance(authorization: str = Header(None), redis: Redis = Depends(get_redis_client),
                      conn: AsyncConnection = Depends(get_psql_conn)):

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid or missing authorization token")
    
    bearer_token = authorization.split(" ")[1]  # Extract the token
    user_id = await redis.get(f"bearer_token:{bearer_token}")
    if not user_id:
        raise HTTPException(status_code=400, detail="User not found for the given token")
    
    # Fetch the user's balance from the database
    try:
        async with conn.cursor() as cursor:
            query = """
            SELECT balance 
            FROM users
            WHERE user_id = %s 
            """
            await cursor.execute(query, (user_id,))
            # Fetch the result
            result = await cursor.fetchone()
        
        if result:
            current_balance = float(result[0])
        else:
            raise HTTPException(status_code=404, detail="Balance not found for the user")

    except psycopg2.Error as db_err:
        logger.exception(f"Database error while fetching balance: {str(db_err)}")
        raise HTTPException(status_code=500, detail="Database error occurred")
    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

    ## return the user balance details
    return {"user_id": user_id, "balance": current_balance}







@router.get("/usage_dashboard")
async def get_usage_dashboard(request: Request, redis: Redis = Depends(get_redis_client), 
                              conn: AsyncConnection = Depends(get_psql_conn)):
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    bearer_token = auth_header.split("Bearer ")[1]

    user_id = await redis.get(f"bearer_token:{bearer_token}")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired bearer token")


    query = """
    SELECT
        model,
        SUM(total_tokens) AS total_tokens,
        SUM(spending) AS total_spending
    FROM logs
    WHERE user_id = %s
        AND timestamp >= NOW() - INTERVAL '1 month'
    GROUP BY model
    ORDER BY total_tokens DESC;
    """

    try:
        async with conn.cursor() as cursor:
            await cursor.execute(query, (user_id,))
            result = await cursor.fetchall()

            usage_data = [{
                "model": row[0],
                "total_tokens": float(row[1]),
                "total_spending": float(row[2]),
            } for row in result]

            return JSONResponse(content={"usage_data": usage_data})

    except Exception as e:
        import traceback
        print("Error in /usage_dashboard:", traceback.format_exc())
        conn.rollback()  # <== This line is important!
        return JSONResponse(content={"error": str(e)}, status_code=500)
