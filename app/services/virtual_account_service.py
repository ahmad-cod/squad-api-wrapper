"""
Virtual Account Service - handles dynamic virtual account operations.

Includes:
- Create VA pool
- Initiate VA transaction
- Requery VA transaction attempts
- Update VA amount/duration
- Simulate VA payment (sandbox)
"""

import logging
from typing import Any, Optional

from app.models.schemas import (
    CreateVirtualAccountPoolRequest,
    CreateVirtualAccountPoolResponse,
    InitiateVATransactionRequest,
    InitiateVATransactionResponse,
    RequeryVATransactionRequest,
    RequeryVATransactionResponse,
    UpdateVAAmountDurationRequest,
    UpdateVAAmountDurationResponse,
    SimulateVAPaymentRequest,
    SimulateVAPaymentResponse,
)
from app.utils.squad_client import SquadAPIClient

logger = logging.getLogger(__name__)


class VirtualAccountService:
    """Service for dynamic virtual account operations."""

    def __init__(self, client: SquadAPIClient):
        """
        Initialize Virtual Account Service.

        Args:
            client: SquadAPIClient instance for HTTP operations
        """
        self.client = client

    async def create_va_pool(self, request: CreateVirtualAccountPoolRequest) -> CreateVirtualAccountPoolResponse:
        """
        Create a pool of dynamic virtual accounts.

        Sets up a pool of accounts to be assigned on a per-transaction basis.
        Optionally configure instant settlement to GTBank account.

        Args:
            request: CreateVirtualAccountPoolRequest with pool configuration

        Returns:
            CreateVirtualAccountPoolResponse with pool details

        Raises:
            SquadAuthenticationError: If API authentication fails
            SquadValidationError: If configuration is invalid
            SquadRequestError: If pool creation fails

        Example:
            >>> request = CreateVirtualAccountPoolRequest(
            ...     beneficiary_account="0147799000",  # GTBank account
            ...     first_name="Acme",
            ...     last_name="Store"
            ... )
            >>> response = await service.create_va_pool(request)
            >>> print(response.data)
        """
        payload = {}

        if request.beneficiary_account:
            payload["beneficiary_account"] = request.beneficiary_account
        if request.first_name:
            payload["first_name"] = request.first_name
        if request.last_name:
            payload["last_name"] = request.last_name

        logger.info(f"Creating virtual account pool with config: {payload}")

        response_data = await self.client.post("/virtual-account/create-dynamic-virtual-account", data=payload)

        logger.info(f"Virtual account pool created successfully")

        return CreateVirtualAccountPoolResponse(
            status=response_data.get("status", 200),
            success=response_data.get("success", False),
            message=response_data.get("message", ""),
            data=response_data.get("data", {}),
        )

    async def initiate_va_transaction(
        self,
        request: InitiateVATransactionRequest,
    ) -> InitiateVATransactionResponse:
        """
        Initiate a dynamic virtual account transaction.

        Assigns a virtual account from the pool for a specific transaction.
        Specifies expected amount and expiration duration.

        Args:
            request: InitiateVATransactionRequest with transaction details

        Returns:
            InitiateVATransactionResponse with assigned VA details

        Raises:
            SquadAuthenticationError: If API authentication fails
            SquadValidationError: If parameters are invalid
            SquadRequestError: If initiation fails

        Example:
            >>> request = InitiateVATransactionRequest(
            ...     amount=100000,  # 1000 NGN
            ...     duration=600,   # 10 minutes
            ...     email="customer@example.com",
            ...     transaction_ref="TXN_20250330_001"
            ... )
            >>> response = await service.initiate_va_transaction(request)
            >>> print(f"Account: {response.data['account_number']}")
            >>> print(f"Expires: {response.data['expires_at']}")
        """
        payload = {
            "amount": request.amount,
            "duration": request.duration,
            "email": request.email,
            "transaction_ref": request.transaction_ref,
        }

        logger.info(
            f"Initiating VA transaction for {request.email}. "
            f"Amount: {request.amount} kobo, Duration: {request.duration}s"
        )

        response_data = await self.client.post(
            "/virtual-account/initiate-dynamic-virtual-account",
            data=payload,
        )

        va_number = response_data.get("data", {}).get("account_number", "N/A")
        logger.info(f"VA transaction initiated. Account: {va_number}")

        return InitiateVATransactionResponse(
            status=response_data.get("status", 200),
            success=response_data.get("success", False),
            message=response_data.get("message", ""),
            data=response_data.get("data", {}),
        )

    async def requery_va_transaction(
        self,
        request: RequeryVATransactionRequest,
    ) -> RequeryVATransactionResponse:
        """
        Requery all attempts for a VA transaction.

        Returns all payment attempts for a transaction including SUCCESS, EXPIRED, and MISMATCH.
        Expired/mismatched transactions are automatically refunded.

        Args:
            request: RequeryVATransactionRequest with transaction reference

        Returns:
            RequeryVATransactionResponse with all transaction attempts

        Raises:
            SquadAuthenticationError: If API authentication fails
            SquadNotFoundError: If transaction not found
            SquadRequestError: If requery fails

        Example:
            >>> request = RequeryVATransactionRequest(transaction_ref="TXN_20250330_001")
            >>> response = await service.requery_va_transaction(request)
            >>> for attempt in response.data.get('rows', []):
            ...     print(f"Status: {attempt['transaction_status']}, Created: {attempt['created_at']}")
        """
        logger.info(f"Requerying VA transaction: {request.transaction_ref}")

        response_data = await self.client.get(
            f"/virtual-account/get-dynamic-virtual-account-transactions/{request.transaction_ref}"
        )

        attempt_count = response_data.get("data", {}).get("count", 0)
        logger.info(f"VA requery complete. Found {attempt_count} attempt(s)")

        return RequeryVATransactionResponse(
            status=response_data.get("status", 200),
            success=response_data.get("success", False),
            message=response_data.get("message", ""),
            data=response_data.get("data", {}),
        )

    async def update_va_amount_duration(
        self,
        request: UpdateVAAmountDurationRequest,
    ) -> UpdateVAAmountDurationResponse:
        """
        Update amount and/or duration of a VA transaction.

        Modify transaction parameters after initiation but before expiration.

        Args:
            request: UpdateVAAmountDurationRequest with new parameters

        Returns:
            UpdateVAAmountDurationResponse with updated transaction details

        Raises:
            SquadAuthenticationError: If API authentication fails
            SquadNotFoundError: If transaction not found
            SquadValidationError: If parameters are invalid
            SquadRequestError: If update fails

        Example:
            >>> request = UpdateVAAmountDurationRequest(
            ...     transaction_reference="TXN_20250330_001",
            ...     amount=150000  # Increase to 1500 NGN
            ... )
            >>> response = await service.update_va_amount_duration(request)
            >>> print(f"New amount: {response.data['amount']}")
        """
        payload = {
            "transaction_reference": request.transaction_reference,
        }

        if request.amount is not None:
            payload["amount"] = request.amount
        if request.duration is not None:
            payload["duration"] = request.duration

        logger.info(f"Updating VA transaction {request.transaction_reference} with: {payload}")

        response_data = await self.client.patch(
            "/virtual-account/update-dynamic-virtual-account-time-and-amount",
            data=payload,
        )

        logger.info(f"VA transaction updated successfully")

        return UpdateVAAmountDurationResponse(
            status=response_data.get("status", 200),
            success=response_data.get("success", False),
            message=response_data.get("message", ""),
            data=response_data.get("data", {}),
        )

    async def simulate_va_payment(self, request: SimulateVAPaymentRequest) -> SimulateVAPaymentResponse:
        """
        Simulate payment into a virtual account (sandbox only).

        Used for testing VA payment flow in sandbox environment.
        IMPORTANT: Only works in sandbox, not production.

        Args:
            request: SimulateVAPaymentRequest with VA and payment details

        Returns:
            SimulateVAPaymentResponse with simulation result

        Raises:
            SquadAuthenticationError: If API authentication fails
            SquadValidationError: If parameters are invalid
            SquadRequestError: If simulation fails

        Example:
            >>> request = SimulateVAPaymentRequest(
            ...     virtual_account_number="4879261135",
            ...     amount=20000  # 200 NGN
            ... )
            >>> response = await service.simulate_va_payment(request)
            >>> print(response.data)
            'Payment successful'
        """
        payload = {
            "virtual_account_number": request.virtual_account_number,
            "amount": str(request.amount),
            "dva": True,  # Dynamic VA flag
        }

        logger.info(f"Simulating VA payment to {request.virtual_account_number} for {request.amount} NGN")

        response_data = await self.client.post("/virtual-account/simulate/payment", data=payload)

        logger.info(f"VA payment simulation successful")

        return SimulateVAPaymentResponse(
            status=response_data.get("status", 200),
            success=response_data.get("success", False),
            message=response_data.get("message", ""),
            data=response_data.get("data", ""),
        )
