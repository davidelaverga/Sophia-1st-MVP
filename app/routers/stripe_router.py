"""
Stripe Webhook Handler

Skeleton implementation for handling Stripe webhook events.
Currently logs events and provides TODO comments for full integration.
"""

import logging
import hmac
import hashlib
from fastapi import APIRouter, Request, HTTPException, Header
from pydantic import BaseModel

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/stripe", tags=["stripe"])


# Stripe event types we care about
HANDLED_EVENTS = [
    "checkout.session.completed",
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.payment_succeeded",
    "invoice.payment_failed",
]


class StripeWebhookEvent(BaseModel):
    """Stripe webhook event structure"""
    id: str
    type: str
    data: dict


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature")
):
    """
    Handle Stripe webhook events.
    
    Currently a skeleton that logs events.
    TODO: Implement full payment processing logic.
    
    Events handled:
    - checkout.session.completed: New subscription
    - customer.subscription.updated: Plan change
    - customer.subscription.deleted: Cancellation
    - invoice.payment_succeeded: Successful payment
    - invoice.payment_failed: Failed payment
    """
    
    try:
        # Get raw body
        body = await request.body()
        
        # TODO: Verify Stripe signature (when STRIPE_WEBHOOK_SECRET is set)
        # stripe_webhook_secret = settings.STRIPE_WEBHOOK_SECRET
        # if stripe_webhook_secret and stripe_signature:
        #     verify_stripe_signature(body, stripe_signature, stripe_webhook_secret)
        
        # Parse event
        event = await request.json()
        event_type = event.get("type")
        event_id = event.get("id")
        
        logger.info(f"[Stripe Webhook] Received event: {event_type} (ID: {event_id})")
        
        # Handle different event types
        if event_type == "checkout.session.completed":
            await handle_checkout_completed(event)
        
        elif event_type == "customer.subscription.created":
            await handle_subscription_created(event)
        
        elif event_type == "customer.subscription.updated":
            await handle_subscription_updated(event)
        
        elif event_type == "customer.subscription.deleted":
            await handle_subscription_deleted(event)
        
        elif event_type == "invoice.payment_succeeded":
            await handle_payment_succeeded(event)
        
        elif event_type == "invoice.payment_failed":
            await handle_payment_failed(event)
        
        else:
            logger.info(f"[Stripe Webhook] Unhandled event type: {event_type}")
        
        return {"status": "success", "event_id": event_id}
        
    except Exception as e:
        logger.error(f"[Stripe Webhook] Error processing webhook: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Webhook processing failed")


async def handle_checkout_completed(event: dict):
    """
    Handle checkout.session.completed event.
    
    This fires when a customer completes the checkout flow.
    """
    logger.info("[Stripe Webhook] Processing checkout.session.completed")
    
    data = event.get("data", {}).get("object", {})
    customer_id = data.get("customer")
    client_reference_id = data.get("client_reference_id")  # This should be user_id
    
    logger.info(f"  Customer: {customer_id}")
    logger.info(f"  User ID: {client_reference_id}")
    
    # TODO: Map Stripe customer to our user_id
    # TODO: Look up which product/price they purchased
    # TODO: Update user.plan_tier in database
    # TODO: Send welcome email
    
    # Example pseudocode:
    # subscription_id = data.get("subscription")
    # if subscription_id:
    #     # Fetch subscription details from Stripe
    #     subscription = stripe.Subscription.retrieve(subscription_id)
    #     price_id = subscription["items"]["data"][0]["price"]["id"]
    #     
    #     # Map price_id to plan_tier
    #     plan_mapping = {
    #         "price_supporter_monthly": "SUPPORTER",
    #         "price_founding_monthly": "FOUNDING_SUPPORTER",
    #     }
    #     plan_tier = plan_mapping.get(price_id, "FREE")
    #     
    #     # Update user in database
    #     supabase.table("users").update({
    #         "plan_tier": plan_tier,
    #         "stripe_customer_id": customer_id,
    #         "stripe_subscription_id": subscription_id,
    #     }).eq("id", client_reference_id).execute()
    
    logger.info("[Stripe Webhook] TODO: Update user plan in database")


async def handle_subscription_created(event: dict):
    """
    Handle customer.subscription.created event.
    """
    logger.info("[Stripe Webhook] Processing customer.subscription.created")
    
    data = event.get("data", {}).get("object", {})
    subscription_id = data.get("id")
    customer_id = data.get("customer")
    
    logger.info(f"  Subscription: {subscription_id}")
    logger.info(f"  Customer: {customer_id}")
    
    # TODO: Update user subscription details
    logger.info("[Stripe Webhook] TODO: Store subscription details")


async def handle_subscription_updated(event: dict):
    """
    Handle customer.subscription.updated event.
    
    This fires when a subscription changes (upgrade, downgrade, renewal).
    """
    logger.info("[Stripe Webhook] Processing customer.subscription.updated")
    
    data = event.get("data", {}).get("object", {})
    subscription_id = data.get("id")
    customer_id = data.get("customer")
    status = data.get("status")
    
    logger.info(f"  Subscription: {subscription_id}")
    logger.info(f"  Customer: {customer_id}")
    logger.info(f"  Status: {status}")
    
    # TODO: Update user plan based on new subscription status
    # TODO: Handle plan upgrades/downgrades
    # TODO: Handle subscription renewals
    
    logger.info("[Stripe Webhook] TODO: Update user plan based on subscription change")


async def handle_subscription_deleted(event: dict):
    """
    Handle customer.subscription.deleted event.
    
    This fires when a subscription is canceled.
    """
    logger.info("[Stripe Webhook] Processing customer.subscription.deleted")
    
    data = event.get("data", {}).get("object", {})
    subscription_id = data.get("id")
    customer_id = data.get("customer")
    
    logger.info(f"  Subscription: {subscription_id}")
    logger.info(f"  Customer: {customer_id}")
    
    # TODO: Downgrade user to FREE plan
    # TODO: Send cancellation email
    # TODO: Schedule account cleanup if needed
    
    logger.info("[Stripe Webhook] TODO: Downgrade user to FREE plan")


async def handle_payment_succeeded(event: dict):
    """
    Handle invoice.payment_succeeded event.
    """
    logger.info("[Stripe Webhook] Processing invoice.payment_succeeded")
    
    data = event.get("data", {}).get("object", {})
    invoice_id = data.get("id")
    customer_id = data.get("customer")
    amount_paid = data.get("amount_paid")
    
    logger.info(f"  Invoice: {invoice_id}")
    logger.info(f"  Customer: {customer_id}")
    logger.info(f"  Amount: ${amount_paid / 100:.2f}")
    
    # TODO: Log successful payment
    # TODO: Send receipt email
    
    logger.info("[Stripe Webhook] TODO: Log payment and send receipt")


async def handle_payment_failed(event: dict):
    """
    Handle invoice.payment_failed event.
    """
    logger.info("[Stripe Webhook] Processing invoice.payment_failed")
    
    data = event.get("data", {}).get("object", {})
    invoice_id = data.get("id")
    customer_id = data.get("customer")
    
    logger.info(f"  Invoice: {invoice_id}")
    logger.info(f"  Customer: {customer_id}")
    
    # TODO: Send payment failure email
    # TODO: Implement retry logic
    # TODO: Pause subscription if multiple failures
    
    logger.info("[Stripe Webhook] TODO: Handle payment failure")


def verify_stripe_signature(payload: bytes, signature: str, secret: str):
    """
    Verify Stripe webhook signature.
    
    Raises HTTPException if signature is invalid.
    """
    # Extract timestamp and signature from header
    parts = signature.split(",")
    timestamp = None
    signatures = []
    
    for part in parts:
        if part.startswith("t="):
            timestamp = part[2:]
        elif part.startswith("v1="):
            signatures.append(part[3:])
    
    if not timestamp or not signatures:
        raise HTTPException(status_code=400, detail="Invalid signature header")
    
    # Compute expected signature
    signed_payload = f"{timestamp}.{payload.decode()}"
    expected_sig = hmac.new(
        secret.encode(),
        signed_payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures
    if expected_sig not in signatures:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    logger.info("[Stripe Webhook] Signature verified successfully")