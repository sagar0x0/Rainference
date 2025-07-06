import os
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from redis.asyncio import Redis
from redis.exceptions import RedisError
import psycopg2
from psycopg import AsyncConnection
from dotenv import load_dotenv
import httpx

from backend.database.db import get_psql_conn, get_redis_client

router = APIRouter()

# Security scheme
security = HTTPBearer()

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,  # Log level: DEBUG to capture all logs, including errors
    format="%(asctime)s - %(levelname)s - %(message)s",  # Log format
)

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# GitHub OAuth configuration
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")

if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
    raise RuntimeError("Missing GitHub OAuth environment variables")


class GitHubAuthRequest(BaseModel):
    """
    Represents a GitHub authentication request.

    Attributes:
        code (str): The GitHub authentication code.
    """
    code: str


# Function to create user, API token, and Bearer token
## in $$dolars by default balance is float
async def create_user(user_email, user_full_name, user_name, balance=1.00):
    redis = await get_redis_client()
    conn = await get_psql_conn()

    try:
        # Generate user details
        user_id = str(uuid.uuid4())  # Generate a unique user ID
        api_token = str(uuid.uuid4())  # Generate a new API token
        bearer_token = str(uuid.uuid4())  # Generate a new Bearer token (for auth)

        # Extract first and last names
        if user_full_name:
            name_parts = user_full_name.split(" ")
            user_fname = name_parts[0]
            user_lname = name_parts[-1] if len(name_parts) > 1 else None
        else:
            user_fname = None
            user_lname = None

        # Open a cursor using context manager to ensure proper handling
        async with conn.cursor() as cursor:
            # Insert user data into the 'users' table
            query = """
            INSERT INTO users (
                user_id, user_name, llm_api_token, bearer_token, fname, lname, email, balance
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (
                user_id,
                user_name,
                api_token,
                bearer_token,
                user_fname,
                user_lname,
                user_email,
                balance,
            )

            await cursor.execute(query, values)  # Execute the query
            await conn.commit()  # Commit the transaction

        print(f"User {user_name} added successfully!")

        user_data = {
            "user_id": user_id,
            "balance": balance,
        }
        llm_api_redis_key = f"llm_api_token:{api_token}"

        # Store llm_api_key map data in Redis
        await redis.hset(llm_api_redis_key, mapping=user_data)

        # Store the Bearer token in Redis (mapping it to user ID)
        await redis.set(f"bearer_token:{bearer_token}", user_id)

        # Log the creation of the user
        logger.info("Created new user: %s with email: %s", user_id, user_email)

    except psycopg2.Error as e:
        print(f"PostgreSQL Database error: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}") from e
    except (ValueError, TypeError) as e:
        logger.exception(
            "Error occurred while creating user with email: %s. Error: %s",
            user_email,
            str(e),
        )
        raise HTTPException(
            status_code=500, detail=f"An error occurred while creating user: {str(e)}"
        ) from e

    return user_id, api_token, bearer_token


# Function to regenerate API token (replace with actual regeneration logic)
async def regenerate_api_token(current_token: str):
    redis = await get_redis_client()
    conn = await get_psql_conn()

    try:
        # Check if the Bearer token is valid (it maps to a user ID)
        user_id = await redis.get(f"bearer_token:{current_token}")

        if not user_id:
            return "Invalid token", None

        # Retrieve the current API token from the user's data
        async with conn.cursor() as cursor:
            # Define the query to fetch the llm_api_token for a given user_id
            query = """
            SELECT llm_api_token, balance
            FROM users
            WHERE user_id = %s
            """
            await cursor.execute(query, (user_id,)) # Execute the query with the user_id param

            # Fetch the result
            result = await cursor.fetchone()

            if result:
                old_api_token, balance = result  # Unpack the result
            else:
                # If no result, return None (user not found)
                return "No API token or balance found for the user", None
            
        # Generate a new API token
        new_api_token = str(uuid.uuid4())  # Create a new unique API token

        # Update a new llm_api_key in psql database
        async with conn.cursor() as cursor:
            # Define the query to update the llm_api_token for a given user_id
            query = """
            UPDATE users
            SET llm_api_token = %s
            WHERE user_id = %s
            """

            # Execute the update query with parameters
            await cursor.execute(query, (new_api_token, user_id))

            # Commit the transaction to make the change persistent
            await conn.commit()

            if cursor.rowcount == 0:
                await conn.rollback()
                return f"No user found with user_id: {user_id}", None

            await conn.commit()

        # Remove the old API token -> user mapping before updating the user data
        await redis.delete(f"llm_api_token:{old_api_token}")

        # Set the new API token to user ID mapping in redis
        await redis.hset(
            f"llm_api_token:{new_api_token}",
            mapping={
                "user_id": user_id,
                "balance": str(balance),
            },
        )

        # Return success status with the new API token
        return "Success", new_api_token

    except RedisError as redis_err:
        logger.exception("Redis error occurred while regenerating API token: %s", str(redis_err))
        return "Redis error", None

    except psycopg2.Error as db_err:
        logger.exception("Database error occurred while regenerating API token: %s", str(db_err))
        return "Database error", None

    except Exception as e:                                                                         # pylint: disable=broad-exception-caught
        logger.exception("Error occurred while regenerating API token: %s", str(e))
        return "An error occurred", None


# GitHub OAuth
@router.post("/auth/github")
async def github_auth(
    request_data: GitHubAuthRequest,
    redis: Redis = Depends(get_redis_client),
    conn: AsyncConnection = Depends(get_psql_conn),
):
    github_token_url = "https://github.com/login/oauth/access_token"
    github_code = request_data.code

    try:
        # Check if the code has already been used (stored in Redis temporarily)
        # Use SETNX to atomically check and set the OAuth code
        if not redis.setnx(f"oauth_code:{github_code}", "used"):
            logger.info("OAuth code %s has already been used.", github_code)
            raise HTTPException(
                status_code=400, detail="This OAuth code has already been used."
            )

        # Set an expiration time for the key after it has been claimed
        redis.expire(f"oauth_code:{github_code}", 300)  # Expiration in 5 minutes

        async with httpx.AsyncClient() as client:
            # Exchange code for access token
            response = await client.post(
                github_token_url,
                headers={"Accept": "application/json"},
                data={
                    "client_id": GITHUB_CLIENT_ID,
                    "client_secret": GITHUB_CLIENT_SECRET,
                    "code": github_code,
                },
            )

            if response.status_code != 200:
                logger.error(
                    "Failed to fetch GitHub token. Status code: %s, Response: %s",
                    response.status_code,
                    response.text,
                )
                raise HTTPException(status_code=400, detail="Failed to fetch GitHub token")

            github_data = response.json()
            access_token = github_data.get("access_token")

            if not access_token:
                logger.error(
                    "Invalid GitHub token response: No access token found :%s",
                    github_data,
                )
                raise HTTPException(status_code=400, detail="Invalid GitHub token")

            # Fetch user info and email
            user_info_response = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            user_email_response = await client.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if user_info_response.status_code != 200:
                logger.error(
                    "Failed to fetch GitHub user info. Status code: %s, Response: %s",
                    user_info_response.status_code,
                    user_info_response.text,
                )
                raise HTTPException(status_code=400, detail="Failed to fetch GitHub user info")

            if user_email_response.status_code != 200:
                logger.error(
                    "Failed to fetch GitHub user email. Status code: %s, Response: %s",
                    user_email_response.status_code,
                    user_email_response.text,
                )
                raise HTTPException(status_code=400, detail="Failed to fetch GitHub user email")

        user_info = user_info_response.json()
        user_email_info = user_email_response.json()

        user_name = user_info.get("login")
        user_full_name = user_info.get("name")
        user_email = (
            user_email_info[0].get("email")
            if isinstance(user_email_info, list)
            else None
        )

        if not user_name:
            logger.error("GitHub user name not found in the response.")
            raise HTTPException(status_code=400, detail="GitHub user name not found")
        if not user_full_name:
            logger.warning(
                "GitHub user full name not found in the response, using a default name."
            )
            user_full_name = None  # You can set a default value or leave it None
        if not user_email:
            logger.error("GitHub user email not found in the response.")
            raise HTTPException(status_code=400, detail="GitHub user user email not found")

        ## combined error handling for production after testing
        # if not user_name or not user_full_name or not user_email:
        #    logger.error("Missing required GitHub user information.")
        #    raise HTTPException(status_code=400, detail="Missing required GitHub user information")

        # Query to check if the user exists
        async with conn.cursor() as cursor:
            query = "SELECT user_id, llm_api_token, bearer_token FROM users WHERE email = %s"
            await cursor.execute(query, (user_email,))
            user_data = await cursor.fetchone()

            if user_data:
                # User exists, return their information
                return {
                    "status": "success",
                    "user_id": user_data[0],
                    "api_token": user_data[1],
                    "bearer_token": user_data[2],
                }

        user_id, api_token, bearer_token = await create_user(
            user_email, user_full_name, user_name
        )

        return {
            "status": "success",
            "user_id": user_id,
            "api_token": api_token,
            "bearer_token": bearer_token,
        }

    except Exception as e:
        logger.exception("Error occurred during GitHub authentication: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"An error occurred: {str(e)}"
        ) from e


# Endpoint to regenerate an API token
@router.post("/regenerate-token/")
async def regenerate_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    try:
        current_token = credentials.credentials
        status, new_token = await regenerate_api_token(current_token)

        if not new_token:
            raise HTTPException(status_code=400, detail=status)

        return {"status": status, "new_api_token": new_token}

    except RedisError as redis_err:
        logger.exception(
            "Redis error occurred while regenerating API keys: %s", str(redis_err)
        )
        raise HTTPException(
            status_code=500,
            detail="A Redis error occurred while processing your request.",
        ) from redis_err

    except Exception as e:
        logger.exception("Error occurred while regenerating API keys: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"An error occurred: {str(e)}"
        ) from e