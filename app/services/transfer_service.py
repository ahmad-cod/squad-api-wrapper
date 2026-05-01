"""
Transfer Service - handles fund transfer operations.

Includes:
- Account lookup (verify recipient before transfer)
- Initiate fund transfer
- Transfer status requery
- List all transfers with pagination
"""

import logging
from typing import Any, Optional

from app.models.schemas import (
    AccountLookupRequest,
    AccountLookupResponse,
    InitiateTransferRequest,
    InitiateTransferResponse,
    RequeryTransferRequest,
    RequeryTransferResponse,
    GetAllTransfersRequest,
    GetAllTransfersResponse,
)
from app.utils.squad_client import SquadAPIClient

logger = logging.getLogger(__name__)


class TransferService:
    """Service for fund transfer operations."""

    def __init__(self, client: SquadAPIClient):
        """
        Initialize Transfer Service.

        Args:
            client: SquadAPIClient instance for HTTP operations
        """
        self.client = client

    async def lookup_account(self, request: AccountLookupRequest) -> AccountLookupResponse:
        """
        Look up and verify a recipient account before transfer.

        IMPORTANT: Always verify account details before initiating transfer to prevent
        sending funds to wrong account.

        Args:
            request: AccountLookupRequest with bank code and account number

        Returns:
            AccountLookupResponse with verified account details

        Raises:
            SquadAuthenticationError: If API authentication fails
            SquadValidationError: If account details are invalid
            SquadRequestError: If lookup fails

        Example:
            >>> request = AccountLookupRequest(
            ...     bank_code="000013",  # GTBank
            ...     account_number="0933384111"
            ... )
            >>> response = await service.lookup_account(request)
            >>> print(response.data['account_name'])
            'JOHN DOE'
        """
        payload = {
            "bank_code": request.bank_code,
            "account_number": request.account_number,
        }

        logger.info(f"Looking up account {request.account_number} at bank code {request.bank_code}")

        response_data = await self.client.post("/payout/account/lookup", data=payload)

        logger.info(f"Account lookup successful for {response_data.get('data', {}).get('account_name', '')}")

        return AccountLookupResponse(
            status=response_data.get("status", 200),
            success=response_data.get("success", False),
            message=response_data.get("message", ""),
            data=response_data.get("data", {}),
        )

    async def initiate_transfer(self, request: InitiateTransferRequest, merchant_id: str) -> InitiateTransferResponse:
        """
        Initiate a fund transfer to a bank account.

        CAUTION: Ensure account has been looked up and verified before calling this.
        Transaction reference MUST include merchant ID as prefix.

        Args:
            request: InitiateTransferRequest with transfer details
            merchant_id: Merchant ID to append to transaction reference

        Returns:
            InitiateTransferResponse with transfer confirmation

        Raises:
            SquadAuthenticationError: If API authentication fails
            SquadValidationError: If transfer parameters are invalid
            SquadRequestError: If transfer initiation fails

        Example:
            >>> request = InitiateTransferRequest(
            ...     transaction_reference="MID123_Transfer001",
            ...     amount=500000,  # 5000 NGN
            ...     bank_code="000013",
            ...     account_number="0933384111",
            ...     account_name="JOHN DOE",
            ...     currency_id="NGN",
            ...     remark="Payment for invoice #001"
            ... )
            >>> response = await service.initiate_transfer(request, "MID123")
            >>> print(response.data['nip_transaction_reference'])
        """
        # Ensure transaction reference includes merchant ID
        if not request.transaction_reference.startswith(merchant_id):
            transaction_ref = f"{merchant_id}_{request.transaction_reference}"
        else:
            transaction_ref = request.transaction_reference

        payload = {
            "transaction_reference": transaction_ref,
            "amount": str(request.amount),
            "bank_code": request.bank_code,
            "account_number": request.account_number,
            "account_name": request.account_name,
            "currency_id": request.currency_id.value,
            "remark": request.remark,
        }

        logger.info(
            f"Initiating transfer of {request.amount} kobo to {request.account_number} "
            f"at bank {request.bank_code}"
        )

        response_data = await self.client.post("/payout/transfer", data=payload)

        logger.info(f"Transfer initiated successfully. Reference: {transaction_ref}")

        return InitiateTransferResponse(
            status=response_data.get("status", 200),
            success=response_data.get("success", False),
            message=response_data.get("message", ""),
            data=response_data.get("data", {}),
        )

    async def requery_transfer(self, request: RequeryTransferRequest) -> RequeryTransferResponse:
        """
        Requery the status of a transfer.

        Use this to check if a transfer that returned status 424 (timeout) eventually succeeded.
        Always requery when uncertain about transfer status.

        Args:
            request: RequeryTransferRequest with transaction reference

        Returns:
            RequeryTransferResponse with updated transfer status

        Raises:
            SquadAuthenticationError: If API authentication fails
            SquadNotFoundError: If transfer not found
            SquadRequestError: If requery fails

        Example:
            >>> request = RequeryTransferRequest(transaction_reference="MID123_Transfer001")
            >>> response = await service.requery_transfer(request)
            >>> print(response.data.get('transaction_status'))
            'success'
        """
        payload = {
            "transaction_reference": request.transaction_reference,
        }

        logger.info(f"Requerying transfer status for {request.transaction_reference}")

        response_data = await self.client.post("/payout/requery", data=payload)

        logger.info(f"Transfer requery complete for {request.transaction_reference}")

        return RequeryTransferResponse(
            status=response_data.get("status", 200),
            success=response_data.get("success", False),
            message=response_data.get("message", ""),
            data=response_data.get("data", {}),
        )

    async def get_all_transfers(self, request: GetAllTransfersRequest) -> GetAllTransfersResponse:
        """
        Get paginated list of all transfers from Squad wallet.

        Retrieve transfer history with optional sorting.

        Args:
            request: GetAllTransfersRequest with pagination parameters

        Returns:
            GetAllTransfersResponse with list of transfers

        Raises:
            SquadAuthenticationError: If API authentication fails
            SquadRequestError: If API request fails

        Example:
            >>> request = GetAllTransfersRequest(page=1, per_page=20, sort_dir="DESC")
            >>> response = await service.get_all_transfers(request)
            >>> for transfer in response.data:
            ...     print(f"Amount: {transfer['amount_debited']}, Status: {transfer['success']}")
        """
        params = {
            "page": request.page,
            "perPage": request.per_page,
            "dir": request.sort_dir,
        }

        logger.info(f"Fetching all transfers. Page: {request.page}, Per page: {request.per_page}")

        response_data = await self.client.get("/payout/list", params=params)

        logger.info(f"Fetched {len(response_data.get('data', []))} transfers")

        return GetAllTransfersResponse(
            status=response_data.get("status", 200),
            success=response_data.get("success", False),
            message=response_data.get("message", ""),
            data=response_data.get("data", []),
        )
