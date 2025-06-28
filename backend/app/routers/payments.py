import os
import stripe
from fastapi import  HTTPException, Request,Header
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from dotenv import load_dotenv
from redis.asyncio import Redis
import psycopg2
from psycopg import AsyncConnection
import httpx
import logging

from database.db import get_redis_client, get_psql_conn

# Load env variables
load_dotenv()

frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,  # Log level: DEBUG to capture all logs, including errors
    format="%(asctime)s - %(levelname)s - %(message)s",  # Log format
)

# Config Stripe env variables
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
stripe_product_id = os.getenv("STRIPE_PRODUCT_ID")
stripe_webhook_secret = os.getenv("STRIPE_ENDPOINT_SECRET")

# pydatic models
class PaymentIntentRequest(BaseModel):
    amount: int  # Amount in cents


# define the router
router = APIRouter()






@router.get("/get-billing-data")
async def get_balance(authorization: str = Header(None), redis: Redis = Depends(get_redis_client),
                      conn: AsyncConnection = Depends(get_psql_conn)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid or missing authorization token")
    
    try:
        # Log the incoming data for debugging (optional)
        print("Received request for balance retrieval")

        bearer_token = authorization.split(" ")[1]  # Extract the token
        user_id = await redis.get(f"bearer_token:{bearer_token}")
        if not user_id:
            raise HTTPException(status_code=400, detail="User not found for the given token")


        # Fetch the user's balance from the database
        async with conn.cursor() as cursor:
            query = """
            SELECT balance 
            FROM users
            WHERE user_id = %s 
            """
            await cursor.execute(query, (user_id,))
            # Fetch the result
            result = await cursor.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="Balance not found for user")
            balance = result[0]
        
        # Check if billing history exists in Redis
        billing_history = await redis.lrange(f"billing_history:{user_id}", 0, -1)
        
        # If billing history is not found, default to an empty list
        if not billing_history:
            billing_history = []  # Default to empty list

        # Return the balance and billing history as a response
        return {"balance": float(balance), "billingHistory": billing_history}

    except Exception as e:
        # Log the exception message for debugging
        print(f"Error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from e



@router.post("/create-payment-intent")
async def create_payment_intent(request: PaymentIntentRequest , authorization: str = Header(None),
                                redis: Redis = Depends(get_redis_client)):
    
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid or missing authorization token")

    try:
        bearer_token = authorization.split(" ")[1]  # Extract the token
        user_id = await redis.get(f"bearer_token:{bearer_token}")

        # Create a payment intent with the amount
        payment_intent = stripe.PaymentIntent.create(
            amount=request.amount,
            currency="usd",
            payment_method_types=["card"],
            metadata={
                "user_id": user_id,
                ## "tokens": tokens, or any other thing 
            },
        )
        return {"clientSecret": payment_intent.client_secret}
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/create-checkout-session") 
async def create_checkout_session(request: PaymentIntentRequest ,authorization: str = Header(None),
                                redis: Redis = Depends(get_redis_client)):

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid or missing authorization token")
    
    try:
        # Log the incoming data for debugging
        print(f"Received request: {request}")

        bearer_token = authorization.split(" ")[1]  # Extract the token
        user_id = await redis.get(f"bearer_token:{bearer_token}")
        if not user_id:
            raise HTTPException(status_code=400, detail="User not found for the given token")

        # Create a Stripe Checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product": stripe_product_id,  # Replace with your Stripe product ID
                        "unit_amount": request.amount,  # Price in cents
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",  # One-time payment
            success_url = f"{frontend_url}/dashboard/success?session_id={{CHECKOUT_SESSION_ID}}",  # Redirect to custom success page
            cancel_url="http://localhost:8000/cancel",  # redirect tom backend 
            metadata={
                "user_id": user_id,
            },
            ## "tokens": tokens, or any other thing 
        )

        return {"checkout_url": checkout_session.url}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/webhook")
async def stripe_webhook(request: Request, redis: Redis = Depends(get_redis_client),
                        conn: AsyncConnection = Depends(get_psql_conn)):
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")

    # Ensure that the Stripe endpoint secret is set in your environment variables
    endpoint_secret = os.getenv("STRIPE_ENDPOINT_SECRET")
    if not endpoint_secret:
        raise HTTPException(status_code=500, detail="Stripe endpoint secret not set")

    try:
        # Verify Stripe webhook signature
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )

        # Handle the checkout session completed event
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]

            # Extract metadata
            user_id = session["metadata"].get("user_id")
            amount_paid = round(session["amount_total"] / 100, 2)  # Amount in dollars

            # Fetch current balance and llm_api_token from Postgres (use 0.0 if not found)
            async with conn.cursor() as cursor:
                query = '''
                SELECT balance , llm_api_token
                FROM users
                WHERE user_id=%s
                '''
                await cursor.execute(query, (user_id,))
                result = await cursor.fetchone()
                current_balance, api_token = result
            
            if result:
                current_balance, api_token = result
                current_balance = float(current_balance) if current_balance else 0.0
            else:
                raise HTTPException(status_code=404, detail="User not found")

            # Update the balance
            new_balance = round(current_balance + amount_paid, 2)

            #Update the balance in psql
            async with conn.cursor() as cursor:
                query = '''
                UPDATE users
                SET balance = %s
                WHERE user_id=%s
                RETURNING balance;
                '''
                await cursor.execute(query, (new_balance, user_id))

                # Commit the transaction to make the update persistent
                await conn.commit()

                psql_balance = await cursor.fetchone()

            # Check if balance was successfully updated
            if not psql_balance:
                await conn.rollback()  # In case of an error, rollback the transaction
                raise HTTPException(status_code=500, detail="Failed to update balance in psql database")

            # Update the balance in Redis 
            await redis.hset(f"llm_api_token:{api_token}", "balance", new_balance)

            # Log to confirm successful update
            print(f"Updated balance for user {user_id}: {new_balance}")

            return {"status": "success", "message": f"Payment of {amount_paid} USD successful, balance updated"}


        # Handle the event
        elif event["type"] == "payment_intent.succeeded":
            payment_intent = event["data"]["object"]
            user_id = payment_intent["metadata"].get("user_id")
            amount_received = round(payment_intent["amount_received"] / 100, 2)

            # Logic to update user tokens, such as updating the database
            # db.update_tokens(user_id, amount_received)

            return {"status": "success", "message": "Payment succeeded, tokens credited"}

         # Default response for unhandled events
        return {"status": "success", "message": "Event received but not handled"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid payload") from e
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail="Invalid signature") from e
    except Exception as e:
        # General error handling to capture unexpected errors
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error") from e 