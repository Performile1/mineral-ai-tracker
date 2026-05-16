"""
Mineral AI Tracker - Stripe Integration (PRD 5.0)
Version: 5.0
Description: Stripe checkout and subscription management
"""

import os
from typing import Optional, Dict, Any
from datetime import datetime
from loguru import logger

try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    logger.warning("Stripe library not installed. Stripe integration will be disabled.")

from fastapi import APIRouter, HTTPException, Request, Query, Depends

from api.deps import get_current_user
from pydantic import BaseModel, Field
import psycopg2
from psycopg2.extras import RealDictCursor
from config import settings


# ============================================================================
# Pydantic Models
# ============================================================================

class CreateCheckoutSessionRequest(BaseModel):
    """Request model for creating Stripe checkout session"""
    price_id: str = Field(..., description="Stripe price ID")
    success_url: Optional[str] = Field(None, description="URL to redirect after success")
    cancel_url: Optional[str] = Field(None, description="URL to redirect after cancel")


class CreateCheckoutSessionResponse(BaseModel):
    """Response model for checkout session creation"""
    success: bool
    checkout_url: Optional[str] = None
    session_id: Optional[str] = None
    message: str


# ============================================================================
# Stripe Client
# ============================================================================

def get_stripe_client():
    """Get Stripe client if available"""
    if not STRIPE_AVAILABLE:
        raise HTTPException(status_code=500, detail="Stripe library not available")
    
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        database=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD
    )


# ============================================================================
# API Routes
# ============================================================================

router = APIRouter(prefix="/api/stripe", tags=["stripe"])

# Stripe Price IDs (configured in Stripe Dashboard)
# Pro subscription monthly price
PRO_MONTHLY_PRICE_ID = os.getenv("STRIPE_PRO_MONTHLY_PRICE_ID", "")
# Pro subscription yearly price
PRO_YEARLY_PRICE_ID = os.getenv("STRIPE_PRO_YEARLY_PRICE_ID", "")


@router.post("/create-checkout-session", response_model=CreateCheckoutSessionResponse)
async def create_checkout_session(
    request: CreateCheckoutSessionRequest,
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    user_id = current_user["id"]  # Critical Hotfix: Use authenticated user_id instead of query param
    """
    Create a Stripe checkout session for Pro subscription
    
    Args:
        request: Checkout session request
        user_id: User ID
    
    Returns:
        Checkout session with URL
    """
    try:
        stripe_client = get_stripe_client()
        
        # Validate price_id
        valid_price_ids = [PRO_MONTHLY_PRICE_ID, PRO_YEARLY_PRICE_ID]
        if request.price_id not in valid_price_ids:
            raise HTTPException(status_code=400, detail="Invalid price ID")
        
        # Get user from database
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        
        if not user:
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if user already has an active subscription
        if user.get("subscription_status") == "active":
            cur.close()
            conn.close()
            return CreateCheckoutSessionResponse(
                success=False,
                message="User already has an active subscription"
            )
        
        # Create or get Stripe customer
        if not user.get("stripe_customer_id"):
            customer = stripe_client.Customer.create(
                email=user.get("email"),
                name=user.get("full_name"),
                metadata={"user_id": user_id}
            )
            stripe_customer_id = customer.id
            
            # Update user with Stripe customer ID
            cur.execute(
                "UPDATE users SET stripe_customer_id = %s WHERE id = %s",
                (stripe_customer_id, user_id)
            )
            conn.commit()
        else:
            stripe_customer_id = user.get("stripe_customer_id")
        
        cur.close()
        conn.close()
        
        # Create checkout session
        checkout_session = stripe_client.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price": request.price_id,
                "quantity": 1,
            }],
            mode="subscription",
            success_url=request.success_url or "http://localhost:3000/checkout/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=request.cancel_url or "http://localhost:3000/checkout/cancel",
            customer=stripe_customer_id,
            metadata={"user_id": user_id},
            subscription_data={
                "metadata": {"user_id": user_id}
            }
        )
        
        logger.info(f"Created checkout session {checkout_session.id} for user {user_id}")
        
        return CreateCheckoutSessionResponse(
            success=True,
            checkout_url=checkout_session.url,
            session_id=checkout_session.id,
            message="Checkout session created successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/subscription-status/{user_id}")
async def get_subscription_status(
    user_id: str,
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    # Critical Hotfix: Prevent cross-user access
    if current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="Cannot access another user's subscription")
    """
    Get current subscription status for a user
    
    Args:
        user_id: User ID
    
    Returns:
        Subscription status
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute(
            "SELECT subscription_tier, subscription_status, subscription_start_date, subscription_end_date FROM users WHERE id = %s",
            (user_id,)
        )
        user = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "subscription_tier": user.get("subscription_tier"),
            "subscription_status": user.get("subscription_status"),
            "subscription_start_date": user.get("subscription_start_date"),
            "subscription_end_date": user.get("subscription_end_date"),
            "is_pro": user.get("subscription_tier") == "pro" and user.get("subscription_status") == "active"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting subscription status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cancel-subscription/{user_id}")
async def cancel_subscription(
    user_id: str,
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    # Critical Hotfix: Prevent cross-user cancellation
    if current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="Cannot cancel another user's subscription")
    """
    Cancel user's subscription (at period end)
    
    Args:
        user_id: User ID
    
    Returns:
        Cancellation status
    """
    try:
        stripe_client = get_stripe_client()
        
        # Get user from database
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        
        if not user:
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail="User not found")
        
        stripe_subscription_id = user.get("stripe_subscription_id")
        
        if not stripe_subscription_id:
            cur.close()
            conn.close()
            raise HTTPException(status_code=400, detail="No active subscription to cancel")
        
        # Cancel subscription in Stripe
        subscription = stripe_client.Subscription.modify(
            stripe_subscription_id,
            cancel_at_period_end=True
        )
        
        # Update user in database
        cur.execute(
            "UPDATE users SET subscription_status = %s, subscription_end_date = %s WHERE id = %s",
            ("canceled", subscription.cancel_at, user_id)
        )
        conn.commit()
        
        cur.close()
        conn.close()
        
        logger.info(f"Canceled subscription {stripe_subscription_id} for user {user_id}")
        
        return {
            "success": True,
            "message": "Subscription will be canceled at period end",
            "cancel_at": subscription.cancel_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error canceling subscription: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhooks for subscription events
    
    Events handled:
    - checkout.session.completed: Subscription created
    - customer.subscription.updated: Subscription updated
    - customer.subscription.deleted: Subscription canceled
    - invoice.payment_succeeded: Payment successful
    - invoice.payment_failed: Payment failed
    """
    try:
        stripe_client = get_stripe_client()
        
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")
        
        webhook_secret = settings.STRIPE_WEBHOOK_SECRET
        if not webhook_secret:
            logger.error("Stripe webhook secret not configured")
            raise HTTPException(status_code=500, detail="Webhook secret not configured")
        
        event = stripe_client.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
        
        logger.info(f"Received Stripe webhook: {event.type}")
        
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        if event.type == "checkout.session.completed":
            session = event.data.object
            user_id = session.metadata.get("user_id")
            
            if user_id:
                # Update user with subscription details
                cur.execute(
                    """
                    UPDATE users 
                    SET subscription_tier = 'pro',
                        subscription_status = 'active',
                        subscription_start_date = NOW(),
                        stripe_subscription_id = %s
                    WHERE id = %s
                    """,
                    (session.subscription, user_id)
                )
                conn.commit()
                logger.info(f"Activated Pro subscription for user {user_id}")
        
        elif event.type == "customer.subscription.updated":
            subscription = event.data.object
            user_id = subscription.metadata.get("user_id")
            
            if user_id:
                # Update subscription status
                cur.execute(
                    """
                    UPDATE users 
                    SET subscription_status = %s
                    WHERE id = %s
                    """,
                    (subscription.status, user_id)
                )
                conn.commit()
                logger.info(f"Updated subscription status for user {user_id}: {subscription.status}")
        
        elif event.type == "customer.subscription.deleted":
            subscription = event.data.object
            user_id = subscription.metadata.get("user_id")
            
            if user_id:
                # Downgrade to basic
                cur.execute(
                    """
                    UPDATE users 
                    SET subscription_tier = 'basic',
                        subscription_status = 'canceled',
                        stripe_subscription_id = NULL
                    WHERE id = %s
                    """,
                    (user_id,)
                )
                conn.commit()
                logger.info(f"Downgraded user {user_id} to Basic tier")
        
        elif event.type == "invoice.payment_failed":
            invoice = event.data.object
            subscription_id = invoice.subscription
            
            # Get subscription to find user_id
            subscription = stripe_client.Subscription.retrieve(subscription_id)
            user_id = subscription.metadata.get("user_id")
            
            if user_id:
                # Mark as past due
                cur.execute(
                    """
                    UPDATE users 
                    SET subscription_status = 'past_due'
                    WHERE id = %s
                    """,
                    (user_id,)
                )
                conn.commit()
                logger.warning(f"Payment failed for user {user_id}")
        
        cur.close()
        conn.close()
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))
