"""
Payment Service - handles all payment-related operations.

Includes:
- Payment initiation (inline checkout)
- Transaction verification
- Card charging (recurring/tokenized)
- Recurring payment cancellation
- Transaction queries
- Test payment simulation
"""

import logging
import uuid
from typing import Any, Optional

from app.models.schemas import (
    ChargeCardRequest,
    ChargeCardResponse,
    CancelRecurringRequest,
    CancelRecurringResponse,
    InitiatePaymentRequest,
    InitiatePaymentResponse,
    QueryTransactionsRequest,
    QueryTransactionsResponse,
    VerifyPaymentRequest,
    VerifyPaymentResponse,
)
from app.utils.squad_client import SquadAPIClient

logger = logging.getLogger(__name__)


class PaymentService:
    """Service for all payment operations."""

    def __init__(self, client: SquadAPIClient):
        """
        Initialize Payment Service.

        Args:
            client: SquadAPIClient instance for HTTP operations
        """
        self.client = client

    async def initiate_payment(self, request: InitiatePaymentRequest) -> InitiatePaymentResponse:
        """
        Initiate a payment transaction.

        Starts the payment flow by creating a transaction and returning a checkout URL.
        The checkout URL displays the payment modal with available channels.

        Args:
            request: InitiatePaymentRequest with payment details

        Returns:
            InitiatePaymentResponse with checkout URL and transaction reference

        Raises:
            SquadAuthenticationError: If API authentication fails
            SquadValidationError: If request validation fails
            SquadRequestError: If API request fails

        Example:
            >>> service = PaymentService(client)
            >>> request = InitiatePaymentRequest(
            ...     amount=50000,
            ...     email="customer@example.com",
            ...     customer_name="John Doe"
            ... )
            >>> response = await service.initiate_payment(request)
            >>> print(response.data['checkout_url'])
            'https://sandbox-pay.squadco.com/...'
        """
        # Generate transaction reference if not provided
        transaction_ref = request.transaction_ref or f"TXN_{uuid.uuid4().hex[:16].upper()}"

        payload = {
            "amount": request.amount,
            "email": request.email,
            "currency": request.currency.value,
            "initiate_type": request.initiate_type.value,
            "transaction_ref": transaction_ref,
        }

        # Add optional fields
        if request.customer_name:
            payload["customer_name"] = request.customer_name
        if request.callback_url:
            payload["callback_url"] = request.callback_url
        if request.payment_channels:
            payload["payment_channels"] = [ch.value for ch in request.payment_channels]
        if request.is_recurring:
            payload["is_recurring"] = request.is_recurring
        if request.metadata:
            payload["metadata"] = request.metadata
        if request.pass_charge is not None:
            payload["pass_charge"] = request.pass_charge
        if request.sub_merchant_id:
            payload["sub_merchant_id"] = request.sub_merchant_id

        logger.info(f"Initiating payment for {request.email} with amount {request.amount} kobo")

        response_data = await self.client.post("/transaction/initiate", data=payload)

        logger.info(f"Payment initiated successfully. Transaction ref: {transaction_ref}")

        return InitiatePaymentResponse(
            status=response_data.get("status", 200),
            message=response_data.get("message", "success"),
            data=response_data.get("data", {}),
        )

    async def verify_payment(self, request: VerifyPaymentRequest) -> VerifyPaymentResponse:
        """
        Verify a payment transaction status.

        Checks if a transaction was successful and retrieves transaction details.

        Args:
            request: VerifyPaymentRequest with transaction reference

        Returns:
            VerifyPaymentResponse with transaction status and details

        Raises:
            SquadAuthenticationError: If API authentication fails
            SquadNotFoundError: If transaction not found
            SquadRequestError: If API request fails

        Example:
            >>> request = VerifyPaymentRequest(transaction_ref="TXN_...")
            >>> response = await service.verify_payment(request)
            >>> if response.data.get('transaction_status') == 'success':
            ...     print("Payment successful!")
        """
        logger.info(f"Verifying payment transaction: {request.transaction_ref}")

        response_data = await self.client.get(f"/transaction/verify/{request.transaction_ref}")

        logger.info(f"Transaction verification complete for {request.transaction_ref}")

        return VerifyPaymentResponse(
            status=response_data.get("status", 200),
            success=response_data.get("success", False),
            data=response_data.get("data", {}),
        )

    async def charge_card(self, request: ChargeCardRequest) -> ChargeCardResponse:
        """
        Charge a tokenized card without re-entering card details.

        Used for recurring payments after initial card tokenization.

        Args:
            request: ChargeCardRequest with amount and token ID

        Returns:
            ChargeCardResponse with charge result and transaction details

        Raises:
            SquadAuthenticationError: If API authentication fails
            SquadValidationError: If request validation fails (invalid token, amount, etc.)
            SquadRequestError: If charge operation fails

        Example:
            >>> request = ChargeCardRequest(
            ...     amount=25000,
            ...     token_id="AUTH_xxxx"
            ... )
            >>> response = await service.charge_card(request)
            >>> print(response.success)
            True
        """
        transaction_ref = request.transaction_ref or f"CHARGE_{uuid.uuid4().hex[:12].upper()}"

        payload = {
            "amount": request.amount,
            "token_id": request.token_id,
        }

        if transaction_ref:
            payload["transaction_ref"] = transaction_ref

        logger.info(f"Charging card with token {request.token_id} for amount {request.amount} kobo")

        response_data = await self.client.post("/transaction/charge_card", data=payload)

        logger.info(f"Card charge successful. Reference: {transaction_ref}")

        return ChargeCardResponse(
            status=response_data.get("status", 200),
            success=response_data.get("success", False),
            message=response_data.get("message", ""),
            data=response_data.get("data", {}),
        )

    async def cancel_recurring(self, request: CancelRecurringRequest) -> CancelRecurringResponse:
        """
        Cancel a recurring card charge authorization.

        Cancels one or more tokenized card authorizations to prevent future charges.

        Args:
            request: CancelRecurringRequest with auth codes to cancel

        Returns:
            CancelRecurringResponse with cancellation result

        Raises:
            SquadAuthenticationError: If API authentication fails
            SquadValidationError: If auth codes are invalid
            SquadRequestError: If cancellation fails

        Example:
            >>> request = CancelRecurringRequest(auth_code=["AUTH_xxxx"])
            >>> response = await service.cancel_recurring(request)
            >>> print(response.success)
            True
        """
        payload = {"auth_code": request.auth_code}

        logger.info(f"Cancelling {len(request.auth_code)} recurring payment(s)")

        response_data = await self.client.patch("/transaction/cancel/recurring", data=payload)

        logger.info(f"Recurring payment cancellation successful")

        return CancelRecurringResponse(
            status=response_data.get("status", 200),
            success=response_data.get("success", False),
            message=response_data.get("message", ""),
            data=response_data.get("data", {}),
        )

    async def query_transactions(self, request: QueryTransactionsRequest) -> QueryTransactionsResponse:
        """
        Query transactions with filters and pagination.

        Retrieve transaction history with optional filters by date, currency, reference, etc.
        Date range must be maximum 1 month.

        Args:
            request: QueryTransactionsRequest with filter parameters

        Returns:
            QueryTransactionsResponse with list of transactions

        Raises:
            SquadAuthenticationError: If API authentication fails
            SquadValidationError: If date range exceeds 1 month
            SquadRequestError: If API request fails

        Example:
            >>> from datetime import datetime, timedelta
            >>> end_date = datetime.now()
            >>> start_date = end_date - timedelta(days=7)
            >>> request = QueryTransactionsRequest(
            ...     start_date=start_date,
            ...     end_date=end_date,
            ...     page=1
            ... )
            >>> response = await service.query_transactions(request)
            >>> for txn in response.data:
            ...     print(txn['transaction_ref'], txn['amount'])
        """
        params = {
            "start_date": request.start_date.isoformat(),
            "end_date": request.end_date.isoformat(),
            "page": request.page,
            "perpage": request.perpage,
        }

        if request.currency:
            params["currency"] = request.currency.value

        if request.reference:
            params["reference"] = request.reference

        logger.info(f"Querying transactions from {request.start_date} to {request.end_date}")

        response_data = await self.client.get("/transaction", params=params)

        logger.info(f"Transaction query completed. Found {len(response_data.get('data', []))} transactions")

        return QueryTransactionsResponse(
            status=response_data.get("status", 200),
            success=response_data.get("success", False),
            message=response_data.get("message", ""),
            data=response_data.get("data", []),
        )

    async def simulate_payment(
        self,
        virtual_account_number: str,
        amount: int,
    ) -> dict[str, Any]:
        """
        Simulate payment into a virtual account (sandbox only).

        Used for testing virtual account payment flow in sandbox environment.

        Args:
            virtual_account_number: 10-digit virtual account number
            amount: Amount in naira (NOT kobo)

        Returns:
            Dictionary with simulation result

        Raises:
            SquadAuthenticationError: If API authentication fails
            SquadValidationError: If parameters are invalid
            SquadRequestError: If simulation fails

        Example:
            >>> result = await service.simulate_payment(
            ...     virtual_account_number="1234567890",
            ...     amount=1000  # 1000 NGN
            ... )
            >>> print(result['data'])
            'Payment successful'
        """
        payload = {
            "virtual_account_number": virtual_account_number,
            "amount": str(amount),
        }

        logger.info(f"Simulating payment to VA {virtual_account_number} for {amount} NGN")

        response_data = await self.client.post("/virtual-account/simulate/payment", data=payload)

        logger.info(f"Payment simulation successful")

        return response_data
