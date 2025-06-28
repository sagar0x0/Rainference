import os 
from fastapi import APIRouter, Depends
from fastapi import Header, Request, WebSocket, HTTPException, WebSocketDisconnect
from typing import List, Dict
from fastapi.responses import HTMLResponse ,JSONResponse,StreamingResponse
from redis.asyncio import Redis
from redis.exceptions import RedisError
import logging
from decimal import Decimal
import httpx
import json
from dotenv import load_dotenv

from database.db import get_redis_client

load_dotenv()

router = APIRouter()

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,  # Log level: DEBUG to capture all logs, including errors
    format="%(asctime)s - %(levelname)s - %(message)s",  # Log format
)

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # A dictionary to map api_tokens to a list of WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, identifier: str, websocket: WebSocket):
        """Add a new WebSocket connection for a given identifier."""
        await websocket.accept()
        if identifier not in self.active_connections:
            self.active_connections[identifier] = []
        self.active_connections[identifier].append(websocket)
        print(f"New WebSocket connection for {identifier}")  # Debugging log

    def disconnect(self, identifier: str, websocket: WebSocket):
        """Remove a specific WebSocket connection for an identifier."""
        if identifier in self.active_connections:
            self.active_connections[identifier].remove(websocket)
            if not self.active_connections[identifier]:  # Remove identifier if no connections remain
                del self.active_connections[identifier]
            print(f"Disconnected WebSocket for {identifier}")  # Debugging log

    async def send_to(self, identifier: str, message: dict):
        """Send a message to all WebSocket connections for an identifier."""
        if identifier in self.active_connections:
            for websocket in self.active_connections[identifier]:
                await websocket.send_json(message)
                print(f"Sent message to {identifier}")  # Debugging log

    async def broadcast(self, message: dict):
        """Send a message to all active WebSocket connections."""
        for connections in self.active_connections.values():
            for websocket in connections:
                await websocket.send_json(message)
                print(f"Broadcasted message to all connections")  # Debugging log

manager = ConnectionManager()



async def validate_token(token: str) -> bool:
    """
    Validates if the provided API token exists in Redis and has sufficient balance.

    Args:
        token (str): The API token to validate.

    Returns:
        bool: True if the token is valid and has a balance > 0.00, otherwise False.
    """
    redis = await get_redis_client() 
    try:
        # Check if the token exists in Redis
        user_info = await redis.hgetall(f"llm_api_token:{token}")
        
        user_id = user_info.get("user_id")
        if not user_id:
            return False  # Token does not exist
        
        # Retrieve and validate balance
        balance_str = user_info.get("balance")
        if not balance_str or not balance_str.strip():
            return False  # Balance field missing or invalid
        
        balance = Decimal(balance_str)

        if balance > Decimal("0.0001"):
            return user_id  # Return user_id if balance is valid
        else:
            return None  # Balance is too low

    except RedisError as redis_err:
        logger.exception(f"Redis error occurred while validating token {token}: {str(redis_err)}")
        return False
    except Exception as e:
        logger.exception(f"Unexpected error occurred while validating token {token}: {str(e)}")
        return False
    



async def perform_inference(
    model: str, 
    prompt: str, 
    max_tokens: int, 
    temperature: float, 
    stream: bool, 
    websocket: WebSocket
):
    try:
        print(f"Starting inference for model: {model}, prompt: {prompt}, stream: {stream}")  # Debugging log

        # Use `stream_kube_data` to handle both streaming and non-streaming cases
        async for data in stream_kube_data(model, prompt, max_tokens, temperature, stream=str(stream), boolStream=stream):
            try:
                data = data.decode("utf-8").strip()  # Decode chunk bytes to string

                if stream:
                    print(f"Streaming token: {data}")  # Debugging log
                    await websocket.send_json(data)
     
                else:
                    print(f"Received full response: {response_data}")  # Debugging log
                    await websocket.send_json(data)
                    break  # Exit after one message for non-streaming

            except Exception as e:
                print(f"Error processing chunk: {e}")
                continue  # Continue processing next chunk

    except HTTPException as e:
        print(f"HTTP exception occurred: {e.detail}")
        await websocket.send_json({"error": f"Inference failed: {e.detail}"})
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        await websocket.send_json({"error": f"An unexpected error occurred: {str(e)}"})





# Kubernetes server URL
KUBE_URL = os.getenv("KUBE_SERVER_URL")

# Function to stream data from Kubernetes server to the client
async def stream_kube_data(model: str, prompt: str, max_tokens: int, temperature: float, stream: str ,boolStream: bool):
    request_data = {
        "model": model,
        "prompt": prompt,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": stream
    }

    async with httpx.AsyncClient() as client:
        if boolStream:
            # Streaming response
            async with client.stream("POST", KUBE_URL, json=request_data) as response:
                if response.status_code != 200:
                    raise HTTPException(status_code=response.status_code, detail="Error from Kubernetes server")
                
                # Yield data as it streams
                async for chunk in response.aiter_bytes():
                    yield chunk
        else:
            # Non-streaming response
            response = await client.post(KUBE_URL, json=request_data)
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Error from Kubernetes server")
            
            # Return raw JSON response
            yield response.json()



# Function to push log data to Redis with expiration
async def push_log_to_redis(log_data):

    redis = await get_redis_client() 
    # Serialize the log data into JSON
    log_data_json = json.dumps(log_data)
    
    # Push log data to the Redis list
    await redis.lpush("logs_buffer", log_data_json)



@router.websocket("/v1/chat/completions")
async def websocket_endpoint(websocket: WebSocket):
    # Step 1: Extract the token from WebSocket headers
    token = websocket.headers.get("Authorization")

    val_token = await validate_token

    if not token or not val_token(token):
        await websocket.close(code=1008, reason="Invalid or missing token")
        return

    # Step 2: Connect the WebSocket for this token
    await manager.connect(token, websocket)
    print(f"Client connected with token: {token}")

    try:
        while True:
            # Step 3: Receive JSON message from the client
            data = await websocket.receive_json()
            print(f"Received: {data}")

            # Extract model and parameters
            model = data.get("model", "default-model")
            prompt = data.get("prompt", [])
            max_tokens = data.get("max_tokens", 11)
            temperature = data.get("temperature", 0.7)
            stream = data.get("stream", True) 

            # Step 4: Send data to Kubernetes server
            # Step 5: Stream response back to the client
            await perform_inference(model, prompt, max_tokens, temperature ,stream, websocket)

    except WebSocketDisconnect:
        # Step 6: Disconnect the specific WebSocket for this token
        manager.disconnect(token, websocket)
        print(f"Client with token {token} disconnected")
    except Exception as e:
        print(f"Error in websocket connection: {str(e)}")
        await websocket.close(code=1011, reason="Internal server error")







@router.post("/v1/chat/completions")
async def chat_completions(request: Request, authorization: str = Header(None)):
    """
    Endpoint for chat completions.

    Args:
        request (Request): Incoming HTTP request with JSON payload.
        authorization (str): Bearer token for API authentication.

    Returns:
        JSONResponse or StreamingResponse: Depending on the "stream" parameter.
    """
    try:
        # Ensure Authorization header is provided
        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization header is required")
        
        # Extract and validate the token
        token = authorization.strip()
        user_id = validate_token(token)
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid or insufficient balance for the token")

        # Get JSON data from the incoming request
        data = await request.json()

        # Extract parameters from the incoming request
        model = data.get("model", "meta-llama/Llama-3.1-8B-Instruct")
        prompt = data.get("prompt", "")
        max_tokens = data.get("max_tokens", 50)
        temperature = data.get("temperature", 0.2)
        stream = data.get("stream", "True")  # Defaults to "True" if not provided
        # Convert the stream parameter to boolean based on "True" string
        boolStream = str(stream).lower() == "true"

        # Validate required fields
        if not prompt:
            raise HTTPException(status_code=400, detail="Prompt is required")

        # Streaming or non-streaming response
        if boolStream:
            return StreamingResponse(
                stream_kube_data(model, prompt, max_tokens, temperature, stream, boolStream),
                media_type="application/json"
            )
        else:
                # Non-streaming response (accumulate and return the full output)
            response_data = None
            async for chunk in stream_kube_data(model, prompt, max_tokens, temperature, stream, boolStream):
                response_data = chunk  # Just store the response directly
            
            # Now response_data is the dictionary from response.json()
            
            # Extract relevant fields for logging
            log_data = {
                "prompt_tokens": response_data.get("usage", {}).get("prompt_tokens"),
                "completion_tokens": response_data.get("usage", {}).get("completion_tokens"),
                "total_tokens": response_data.get("usage", {}).get("total_tokens"),
                "timestamp": response_data.get("created"),
                "user_id": user_id,
                "model": response_data.get("model"),
                "log_id": response_data.get("id"),
            }

            # Push the log data to Redis
            await push_log_to_redis(log_data)

            # Return the complete response data as JSON
            return JSONResponse(content=response_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {e}")

