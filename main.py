"""
Squad API Wrapper - Main FastAPI application.

Modular service-based wrapper for Squad payment gateway.
Includes endpoints for payments, transfers, refunds, and virtual accounts.

Environment Variables:
    SQUAD_SECRET_KEY: Squad API secret key
    SQUAD_BASE_URL: Squad API base URL (default: sandbox)
    ENVIRONMENT: Environment type (sandbox, production)
    MERCHANT_ID: Merchant ID for transfers
Read more at https://docs.squadco.com/
"""

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.models.schemas import (
    InitiatePaymentRequest,
    VerifyPaymentRequest,
    ChargeCardRequest,
    CancelRecurringRequest,
    QueryTransactionsRequest,
    AccountLookupRequest,
    InitiateTransferRequest,
    RequeryTransferRequest,
    GetAllTransfersRequest,
    InitiateRefundRequest,
    CreateVirtualAccountPoolRequest,
    InitiateVATransactionRequest,
    RequeryVATransactionRequest,
    UpdateVAAmountDurationRequest,
    SimulateVAPaymentRequest,
)
from app.services.payment_service import PaymentService
from app.services.transfer_service import TransferService
from app.services.refund_service import RefundService
from app.services.virtual_account_service import VirtualAccountService
from app.services.webhook_service import WebhookService
from app.utils.squad_client import SquadAPIClient
from app.utils.exceptions import SquadAPIException
from app.utils.webhooks import extract_webhook_signature_from_headers

# Load environment variables
load_dotenv()

# Configuration
SQUAD_SECRET_KEY = os.getenv("SQUAD_SECRET_KEY", "sk_test_your_key_here")
SQUAD_BASE_URL = os.getenv("SQUAD_BASE_URL", "https://sandbox-api-d.squadco.com")
ENVIRONMENT = os.getenv("ENVIRONMENT", "sandbox")
MERCHANT_ID = os.getenv("MERCHANT_ID", "MERCHANT_ID")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize services
squad_client = SquadAPIClient(secret_key=SQUAD_SECRET_KEY, base_url=SQUAD_BASE_URL)
payment_service = PaymentService(client=squad_client)
transfer_service = TransferService(client=squad_client)
refund_service = RefundService(client=squad_client)
va_service = VirtualAccountService(client=squad_client)
webhook_service = WebhookService(secret_key=SQUAD_SECRET_KEY)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    logger.info(f"Squad API wrapper starting. Environment: {ENVIRONMENT}")
    yield
    logger.info("Squad API wrapper shutting down")


# Create FastAPI app
app = FastAPI(
    title="Squad Payment API Wrapper",
    description="Comprehensive wrapper for Squad payment gateway with payments, transfers, refunds, and virtual accounts",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# ERROR HANDLERS
# ============================================================================


@app.exception_handler(SquadAPIException)
async def squad_api_exception_handler(request: Request, exc: SquadAPIException):
    """Handle Squad API exceptions."""
    logger.error(f"Squad API Error: {exc}")
    return JSONResponse(
        status_code=exc.status_code or 400,
        content={
            "success": False,
            "error": exc.message,
            "details": exc.details,
        },
    )


# ============================================================================
# HEALTH & INFO ENDPOINTS
# ============================================================================


@app.get("/")
async def root():
    """Welcome endpoint with API information."""
    return {
        "message": "Welcome to Squad Payment API Wrapper",
        "version": "1.0.0",
        "environment": ENVIRONMENT,
        "endpoints": {
            "payments": "/payments",
            "transfers": "/transfers",
            "refunds": "/refunds",
            "virtual_accounts": "/virtual-accounts",
            "webhooks": "/webhooks",
        },
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "squad-api-wrapper"}


# ============================================================================
# PAYMENT ENDPOINTS
# ============================================================================


@app.post("/payments/initiate")
async def initiate_payment(request: InitiatePaymentRequest):
    """
    Initiate a payment transaction.

    Creates a transaction and returns a checkout URL for inline payment modal.
    The customer can pay via card, transfer, USSD, or bank account.
    """
    try:
        response = await payment_service.initiate_payment(request)
        return response.model_dump()
    except Exception as e:
        logger.error(f"Error initiating payment: {str(e)}")
        raise


@app.get("/payments/verify/{transaction_ref}")
async def verify_payment(transaction_ref: str):
    """
    Verify payment transaction status.

    Check if a transaction was successful and retrieve transaction details.
    """
    try:
        request = VerifyPaymentRequest(transaction_ref=transaction_ref)
        response = await payment_service.verify_payment(request)
        return response.model_dump()
    except Exception as e:
        logger.error(f"Error verifying payment: {str(e)}")
        raise


@app.post("/payments/charge-card")
async def charge_card(request: ChargeCardRequest):
    """
    Charge a previously tokenized card.

    Use this endpoint to charge a card without collecting card details again.
    Requires a token_id from initial card tokenization.
    """
    try:
        response = await payment_service.charge_card(request)
        return response.model_dump()
    except Exception as e:
        logger.error(f"Error charging card: {str(e)}")
        raise


@app.patch("/payments/cancel-recurring")
async def cancel_recurring(request: CancelRecurringRequest):
    """
    Cancel recurring card payment authorization.

    Prevents future charges on a tokenized card by cancelling its authorization.
    """
    try:
        response = await payment_service.cancel_recurring(request)
        return response.model_dump()
    except Exception as e:
        logger.error(f"Error cancelling recurring payment: {str(e)}")
        raise


@app.post("/payments/query")
async def query_transactions(request: QueryTransactionsRequest):
    """
    Query transactions with filters and pagination.

    Retrieve transaction history filtered by date, currency, reference, etc.
    Date range must be maximum 1 month.
    """
    try:
        response = await payment_service.query_transactions(request)
        return response.model_dump()
    except Exception as e:
        logger.error(f"Error querying transactions: {str(e)}")
        raise


# ============================================================================
# TRANSFER ENDPOINTS
# ============================================================================


@app.post("/transfers/lookup-account")
async def lookup_account(request: AccountLookupRequest):
    """
    Lookup and verify recipient account details.

    Always verify account details before initiating transfer to prevent
    sending funds to wrong account.
    """
    try:
        response = await transfer_service.lookup_account(request)
        return response.model_dump()
    except Exception as e:
        logger.error(f"Error looking up account: {str(e)}")
        raise


@app.post("/transfers/initiate")
async def initiate_transfer(request: InitiateTransferRequest):
    """
    Initiate a fund transfer to a bank account.

    Transfers funds from Squad wallet to specified bank account.
    Account must be verified via lookup_account first.
    """
    try:
        response = await transfer_service.initiate_transfer(request, merchant_id=MERCHANT_ID)
        return response.model_dump()
    except Exception as e:
        logger.error(f"Error initiating transfer: {str(e)}")
        raise


@app.post("/transfers/requery/{transaction_ref}")
async def requery_transfer(transaction_ref: str):
    """
    Requery transfer status.

    Use this to check if a transfer that returned timeout (424) eventually succeeded.
    """
    try:
        request = RequeryTransferRequest(transaction_reference=transaction_ref)
        response = await transfer_service.requery_transfer(request)
        return response.model_dump()
    except Exception as e:
        logger.error(f"Error requerying transfer: {str(e)}")
        raise


@app.get("/transfers/all")
async def get_all_transfers(page: int = 1, per_page: int = 20, sort_dir: str = "DESC"):
    """
    Get paginated list of all transfers.

    Retrieve transfer history with optional sorting by date.
    """
    try:
        request = GetAllTransfersRequest(page=page, per_page=per_page, sort_dir=sort_dir)
        response = await transfer_service.get_all_transfers(request)
        return response.model_dump()
    except Exception as e:
        logger.error(f"Error fetching transfers: {str(e)}")
        raise


# ============================================================================
# REFUND ENDPOINTS
# ============================================================================


@app.post("/refunds/initiate")
async def initiate_refund(request: InitiateRefundRequest):
    """
    Initiate a refund for a transaction.

    Supports full and partial refunds. Partial refunds require refund_amount.
    """
    try:
        response = await refund_service.initiate_refund(request)
        return response.model_dump()
    except Exception as e:
        logger.error(f"Error initiating refund: {str(e)}")
        raise


# ============================================================================
# VIRTUAL ACCOUNT ENDPOINTS
# ============================================================================


@app.post("/virtual-accounts/pool/create")
async def create_va_pool(request: CreateVirtualAccountPoolRequest):
    """
    Create a pool of dynamic virtual accounts.

    Sets up accounts to be assigned on a per-transaction basis.
    Optionally configure instant settlement to GTBank account.
    """
    try:
        response = await va_service.create_va_pool(request)
        return response.model_dump()
    except Exception as e:
        logger.error(f"Error creating VA pool: {str(e)}")
        raise


@app.post("/virtual-accounts/initiate")
async def initiate_va_transaction(request: InitiateVATransactionRequest):
    """
    Initiate a dynamic virtual account transaction.

    Assigns a virtual account from pool for a specific transaction.
    Specify expected amount and expiration duration (in seconds).
    """
    try:
        response = await va_service.initiate_va_transaction(request)
        return response.model_dump()
    except Exception as e:
        logger.error(f"Error initiating VA transaction: {str(e)}")
        raise


@app.get("/virtual-accounts/requery/{transaction_ref}")
async def requery_va_transaction(transaction_ref: str):
    """
    Requery all attempts for a virtual account transaction.

    Returns all payment attempts including SUCCESS, EXPIRED, and MISMATCH.
    """
    try:
        request = RequeryVATransactionRequest(transaction_ref=transaction_ref)
        response = await va_service.requery_va_transaction(request)
        return response.model_dump()
    except Exception as e:
        logger.error(f"Error requerying VA transaction: {str(e)}")
        raise


@app.patch("/virtual-accounts/update")
async def update_va_amount_duration(request: UpdateVAAmountDurationRequest):
    """
    Update amount and/or duration of a virtual account transaction.

    Modify transaction parameters after initiation but before expiration.
    """
    try:
        response = await va_service.update_va_amount_duration(request)
        return response.model_dump()
    except Exception as e:
        logger.error(f"Error updating VA transaction: {str(e)}")
        raise


@app.post("/virtual-accounts/simulate-payment")
async def simulate_va_payment(request: SimulateVAPaymentRequest):
    """
    Simulate payment into a virtual account (sandbox only).

    Used for testing VA payment flow in sandbox environment.
    """
    try:
        response = await va_service.simulate_va_payment(request)
        return response.model_dump()
    except Exception as e:
        logger.error(f"Error simulating VA payment: {str(e)}")
        raise


# ============================================================================
# WEBHOOK ENDPOINTS
# ============================================================================


@app.post("/webhooks/payment")
async def handle_payment_webhook(
    request: Request,
    x_squad_encrypted_body: str = Header(...),
):
    """
    Webhook endpoint for payment events.

    Receives and processes payment completion/failure events from Squad.
    Signature must be validated via x-squad-encrypted-body header.
    """
    try:
        payload = await request.json()

        # Validate webhook signature
        webhook_service.validate_webhook_signature(
            payload=payload,
            received_signature=x_squad_encrypted_body,
        )

        # Process webhook
        response = await webhook_service.process_payment_webhook(payload)
        logger.info(f"Payment webhook processed: {response.reference}")

        return response.model_dump()

    except ValueError as e:
        logger.error(f"Webhook signature validation failed: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    except Exception as e:
        logger.error(f"Error processing payment webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process webhook")


@app.post("/webhooks/virtual-account")
async def handle_va_webhook(
    request: Request,
    x_squad_encrypted_body: str = Header(...),
):
    """
    Webhook endpoint for virtual account events.

    Receives and processes SUCCESS, EXPIRED, MISMATCH events for VA transactions.
    Signature must be validated via x-squad-encrypted-body header.
    """
    try:
        payload = await request.json()

        # Validate webhook signature
        webhook_service.validate_webhook_signature(
            payload=payload,
            received_signature=x_squad_encrypted_body,
        )

        # Process webhook
        response = await webhook_service.process_va_webhook(payload)
        logger.info(f"VA webhook processed: {response.reference}")

        return response.model_dump()

    except ValueError as e:
        logger.error(f"Webhook signature validation failed: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    except Exception as e:
        logger.error(f"Error processing VA webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process webhook")