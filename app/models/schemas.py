"""
Pydantic models and schemas for Squad API requests and responses.

Organized by feature domain: Payments, Transfers, Refunds, Virtual Accounts, Webhooks.
All models include type hints, validation rules, and example values.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, EmailStr, field_validator


# ============================================================================
# ENUMS
# ============================================================================


class CurrencyEnum(str, Enum):
    """Supported currencies."""

    NGN = "NGN"
    USD = "USD"


class PaymentChannelEnum(str, Enum):
    """Available payment channels."""

    CARD = "card"
    TRANSFER = "transfer"
    USSD = "ussd"
    BANK = "bank"


class InitiateTypeEnum(str, Enum):
    """Payment initiation types."""

    INLINE = "inline"


class TransactionStatusEnum(str, Enum):
    """Transaction status values."""

    SUCCESS = "success"
    PENDING = "pending"
    FAILED = "failed"


class RefundTypeEnum(str, Enum):
    """Refund types."""

    FULL = "Full"
    PARTIAL = "Partial"


class VirtualAccountStatusEnum(str, Enum):
    """Virtual account transaction statuses."""

    SUCCESS = "SUCCESS"
    EXPIRED = "EXPIRED"
    MISMATCH = "MISMATCH"


# ============================================================================
# PAYMENT MODELS
# ============================================================================


class InitiatePaymentRequest(BaseModel):
    """Request to initiate a payment transaction."""

    amount: int = Field(..., gt=0, description="Amount in kobo/cent (lowest currency unit)")
    email: EmailStr = Field(..., description="Customer email address")
    currency: CurrencyEnum = Field(default=CurrencyEnum.NGN, description="Transaction currency")
    initiate_type: InitiateTypeEnum = Field(default=InitiateTypeEnum.INLINE)
    transaction_ref: Optional[str] = Field(None, max_length=100, description="Unique merchant transaction reference")
    customer_name: Optional[str] = Field(None, max_length=200, description="Customer name")
    callback_url: Optional[str] = Field(None, description="URL to redirect after payment completion")
    payment_channels: Optional[list[PaymentChannelEnum]] = Field(
        None, description="Available payment channels ['card', 'transfer', 'ussd', 'bank']"
    )
    is_recurring: bool = Field(default=False, description="Enable card tokenization for recurring payments")
    metadata: Optional[dict[str, Any]] = Field(None, description="Custom metadata to track with transaction")
    pass_charge: bool = Field(default=False, description="Pass charges to customer (True) or merchant (False)")
    sub_merchant_id: Optional[str] = Field(None, description="Sub-merchant ID for aggregators")


class InitiatePaymentResponse(BaseModel):
    """Response from payment initiation."""

    status: int = Field(description="HTTP status code")
    message: str = Field(description="Response message")
    data: dict[str, Any] = Field(description="Response data including checkout_url, transaction_ref, etc.")


class VerifyPaymentRequest(BaseModel):
    """Request to verify a payment transaction."""

    transaction_ref: str = Field(..., description="Transaction reference to verify")


class VerifyPaymentResponse(BaseModel):
    """Response from payment verification."""

    status: int = Field(description="HTTP status code")
    success: bool = Field(description="Whether verification was successful")
    data: dict[str, Any] = Field(description="Transaction details")


class ChargeCardRequest(BaseModel):
    """Request to charge a tokenized card."""

    amount: int = Field(..., gt=0, description="Amount in kobo/cent")
    token_id: str = Field(..., description="Card token ID from initial tokenization")
    transaction_ref: Optional[str] = Field(None, description="Unique transaction reference for this charge")


class ChargeCardResponse(BaseModel):
    """Response from card charge."""

    status: int = Field(description="HTTP status code")
    success: bool = Field(description="Whether charge was successful")
    message: str = Field(description="Response message")
    data: dict[str, Any] = Field(description="Transaction details")


class CancelRecurringRequest(BaseModel):
    """Request to cancel recurring card charge."""

    auth_code: list[str] = Field(..., description="List of authorization codes to cancel")


class CancelRecurringResponse(BaseModel):
    """Response from cancel recurring request."""

    status: int = Field(description="HTTP status code")
    success: bool = Field(description="Whether cancellation was successful")
    message: str = Field(description="Response message")
    data: dict[str, Any] = Field(description="Cancelled auth codes")


class QueryTransactionsRequest(BaseModel):
    """Request to query transactions with filters."""

    start_date: datetime = Field(..., description="Start date for transaction query")
    end_date: datetime = Field(..., description="End date for transaction query")
    currency: Optional[CurrencyEnum] = Field(None, description="Filter by currency")
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    perpage: int = Field(default=20, ge=1, le=100, description="Records per page")
    reference: Optional[str] = Field(None, description="Filter by transaction reference")

    @field_validator("end_date")
    def validate_dates(cls, end_date, info):
        """Ensure end_date is after start_date."""
        if "start_date" in info.data and end_date <= info.data["start_date"]:
            raise ValueError("end_date must be after start_date")
        return end_date


class QueryTransactionsResponse(BaseModel):
    """Response from transaction query."""

    status: int = Field(description="HTTP status code")
    success: bool = Field(description="Whether query was successful")
    message: str = Field(description="Response message")
    data: list[dict[str, Any]] = Field(description="List of transactions")


# ============================================================================
# TRANSFER MODELS
# ============================================================================


class AccountLookupRequest(BaseModel):
    """Request to lookup/verify account details before transfer."""

    bank_code: str = Field(..., max_length=6, description="NIP code identifying the bank")
    account_number: str = Field(..., regex=r"^\d{10}$", description="10-digit NUBAN account number")


class AccountLookupResponse(BaseModel):
    """Response from account lookup."""

    status: int = Field(description="HTTP status code")
    success: bool = Field(description="Whether lookup was successful")
    message: str = Field(description="Response message")
    data: dict[str, Any] = Field(
        description="Account details including account_name and account_number"
    )


class InitiateTransferRequest(BaseModel):
    """Request to initiate fund transfer."""

    transaction_reference: str = Field(..., description="Unique transaction reference (must include Merchant ID)")
    amount: int = Field(..., gt=0, description="Amount in kobo")
    bank_code: str = Field(..., max_length=6, description="NIP code identifying the bank")
    account_number: str = Field(..., regex=r"^\d{10}$", description="10-digit NUBAN account number")
    account_name: str = Field(..., description="Account name (from lookup)")
    currency_id: CurrencyEnum = Field(default=CurrencyEnum.NGN, description="Currency (only NGN supported)")
    remark: str = Field(..., max_length=200, description="Transfer remark/reason")


class InitiateTransferResponse(BaseModel):
    """Response from transfer initiation."""

    status: int = Field(description="HTTP status code")
    success: bool = Field(description="Whether transfer was initiated")
    message: str = Field(description="Response message")
    data: dict[str, Any] = Field(
        description="Transfer details including nip_transaction_reference"
    )


class RequeryTransferRequest(BaseModel):
    """Request to requery transfer status."""

    transaction_reference: str = Field(..., description="Transaction reference to requery")


class RequeryTransferResponse(BaseModel):
    """Response from transfer requery."""

    status: int = Field(description="HTTP status code")
    success: bool = Field(description="Whether requery was successful")
    message: str = Field(description="Response message")
    data: dict[str, Any] = Field(description="Updated transfer status")


class GetAllTransfersRequest(BaseModel):
    """Request to get all transfers."""

    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=20, ge=1, le=100, description="Records per page")
    sort_dir: str = Field(default="DESC", regex="^(ASC|DESC)$", description="Sort direction")


class GetAllTransfersResponse(BaseModel):
    """Response containing list of transfers."""

    status: int = Field(description="HTTP status code")
    success: bool = Field(description="Whether query was successful")
    message: str = Field(description="Response message")
    data: list[dict[str, Any]] = Field(description="List of transfer records")


# ============================================================================
# REFUND MODELS
# ============================================================================


class InitiateRefundRequest(BaseModel):
    """Request to initiate a refund."""

    gateway_transaction_ref: str = Field(..., description="Gateway transaction reference")
    transaction_ref: str = Field(..., description="Merchant transaction reference")
    refund_type: RefundTypeEnum = Field(..., description="'Full' or 'Partial'")
    reason_for_refund: str = Field(..., max_length=500, description="Reason for refund")
    refund_amount: Optional[int] = Field(None, gt=0, description="Amount in kobo (required for Partial refunds)")

    @field_validator("refund_amount")
    def validate_refund_amount(cls, refund_amount, info):
        """Ensure partial refunds have an amount."""
        if info.data.get("refund_type") == RefundTypeEnum.PARTIAL and refund_amount is None:
            raise ValueError("refund_amount is required for Partial refunds")
        return refund_amount


class InitiateRefundResponse(BaseModel):
    """Response from refund initiation."""

    status: int = Field(description="HTTP status code")
    success: bool = Field(description="Whether refund was initiated")
    message: str = Field(description="Response message")
    data: dict[str, Any] = Field(description="Refund details including refund_reference")


# ============================================================================
# VIRTUAL ACCOUNT MODELS
# ============================================================================


class CreateVirtualAccountPoolRequest(BaseModel):
    """Request to create dynamic virtual account pool."""

    beneficiary_account: Optional[str] = Field(None, regex=r"^\d{10}$", description="GTBank account for instant settlement")
    first_name: Optional[str] = Field(None, max_length=100, description="Custom first name for VA")
    last_name: Optional[str] = Field(None, max_length=100, description="Custom last name for VA")


class CreateVirtualAccountPoolResponse(BaseModel):
    """Response from VA pool creation."""

    status: int = Field(description="HTTP status code")
    success: bool = Field(description="Whether creation was successful")
    message: str = Field(description="Response message")
    data: dict[str, Any] = Field(description="Account pool details")


class InitiateVATransactionRequest(BaseModel):
    """Request to initiate dynamic virtual account transaction."""

    amount: int = Field(..., gt=0, description="Amount in kobo")
    duration: int = Field(..., gt=0, description="Duration in seconds before expiration")
    email: EmailStr = Field(..., description="Customer email for notification")
    transaction_ref: str = Field(..., max_length=100, description="Unique merchant transaction reference")


class InitiateVATransactionResponse(BaseModel):
    """Response from VA transaction initiation."""

    status: int = Field(description="HTTP status code")
    success: bool = Field(description="Whether initiation was successful")
    message: str = Field(description="Response message")
    data: dict[str, Any] = Field(
        description="VA details including account_number, account_name, expires_at"
    )


class RequeryVATransactionRequest(BaseModel):
    """Request to requery virtual account transaction."""

    transaction_ref: str = Field(..., description="Transaction reference to requery")


class VATransactionAttempt(BaseModel):
    """Single transaction attempt in VA requery response."""

    transaction_status: VirtualAccountStatusEnum = Field(description="Status: SUCCESS, EXPIRED, or MISMATCH")
    transaction_reference: str = Field(description="Transaction reference")
    created_at: datetime = Field(description="When this attempt occurred")
    refund: Optional[bool] = Field(None, description="Whether refund was issued")


class RequeryVATransactionResponse(BaseModel):
    """Response from VA transaction requery."""

    status: int = Field(description="HTTP status code")
    success: bool = Field(description="Whether requery was successful")
    message: str = Field(description="Response message")
    data: dict[str, Any] = Field(
        description="Transaction attempts with count and rows"
    )


class UpdateVAAmountDurationRequest(BaseModel):
    """Request to update virtual account amount/duration."""

    transaction_reference: str = Field(..., description="Transaction reference")
    amount: Optional[int] = Field(None, gt=0, description="New amount in kobo")
    duration: Optional[int] = Field(None, gt=0, description="New duration in seconds")

    @field_validator("duration", "amount")
    def at_least_one_field(cls, value, info):
        """Ensure at least one field is provided."""
        if value is None and all(info.data.get(f) is None for f in ["amount", "duration"] if f != info.field_name):
            raise ValueError("At least one of amount or duration must be provided")
        return value


class UpdateVAAmountDurationResponse(BaseModel):
    """Response from VA update."""

    status: int = Field(description="HTTP status code")
    success: bool = Field(description="Whether update was successful")
    message: str = Field(description="Response message")
    data: dict[str, Any] = Field(description="Updated transaction details")


class SimulateVAPaymentRequest(BaseModel):
    """Request to simulate payment into virtual account (sandbox only)."""

    virtual_account_number: str = Field(..., regex=r"^\d{10}$", description="10-digit VA number")
    amount: int = Field(..., gt=0, description="Amount in naira (not kobo)")


class SimulateVAPaymentResponse(BaseModel):
    """Response from simulated payment."""

    status: int = Field(description="HTTP status code")
    success: bool = Field(description="Whether simulation was successful")
    message: str = Field(description="Response message")
    data: str = Field(description="Result message")


# ============================================================================
# WEBHOOK MODELS
# ============================================================================


class WebhookSignatureValidation(BaseModel):
    """Webhook signature validation data."""

    received_signature: str = Field(..., description="Signature from x-squad-encrypted-body header")
    secret_key: str = Field(..., description="Secret key for validation")
    payload: dict[str, Any] = Field(..., description="Webhook payload to verify")


class PaymentWebhookPayload(BaseModel):
    """Payment webhook event payload."""

    Event: str = Field(description="Event type (e.g., 'charge_successful')")
    TransactionRef: str = Field(description="Transaction reference")
    Body: dict[str, Any] = Field(description="Event details")


class VAWebhookPayload(BaseModel):
    """Virtual account webhook event payload."""

    transaction_status: VirtualAccountStatusEnum = Field(description="SUCCESS, EXPIRED, or MISMATCH")
    merchant_reference: str = Field(description="Merchant's transaction reference")
    transaction_reference: str = Field(description="Squad's transaction reference")
    amount_received: str = Field(description="Amount received in NGN")
    merchant_amount: str = Field(description="Merchant amount in NGN")
    email: EmailStr = Field(description="Customer email")
    merchant_id: str = Field(description="Merchant ID")
    date: datetime = Field(description="Event timestamp")
    sender_name: Optional[str] = Field(None, description="Name of sender (if available)")


class WebhookResponse(BaseModel):
    """Standard webhook processing response."""

    success: bool = Field(description="Whether webhook was processed successfully")
    message: str = Field(description="Processing message")
    reference: str = Field(description="Transaction/webhook reference")
