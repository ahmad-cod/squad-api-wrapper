"""
Refund Service - handles refund operations.

Includes:
- Initiate full or partial refunds
- Track refund status
"""

import logging
from typing import Any

from app.models.schemas import (
    InitiateRefundRequest,
    InitiateRefundResponse,
)
from app.utils.squad_client import SquadAPIClient

logger = logging.getLogger(__name__)


class RefundService:
    """Service for refund operations."""

    def __init__(self, client: SquadAPIClient):
        """
        Initialize Refund Service.

        Args:
            client: SquadAPIClient instance for HTTP operations
        """
        self.client = client

    async def initiate_refund(self, request: InitiateRefundRequest) -> InitiateRefundResponse:
        """
        Initiate a refund for a transaction.

        Supports both full and partial refunds with reason tracking.
        For partial refunds, refund_amount must be specified in kobo.

        Args:
            request: InitiateRefundRequest with refund parameters

        Returns:
            InitiateRefundResponse with refund reference and status

        Raises:
            SquadAuthenticationError: If API authentication fails
            SquadValidationError: If refund parameters are invalid
            SquadRequestError: If refund initiation fails

        Example (Full Refund):
            >>> request = InitiateRefundRequest(
            ...     gateway_transaction_ref="SQOKOY1708696818297_1_1",
            ...     transaction_ref="SQOKOY1708696818297",
            ...     refund_type=RefundTypeEnum.FULL,
            ...     reason_for_refund="Customer requested cancellation"
            ... )
            >>> response = await service.initiate_refund(request)
            >>> print(response.data['refund_reference'])
            'REFUND-SQOKOY1708696818297_1_1'

        Example (Partial Refund):
            >>> request = InitiateRefundRequest(
            ...     gateway_transaction_ref="SQOKOY1708696818297_1_1",
            ...     transaction_ref="SQOKOY1708696818297",
            ...     refund_type=RefundTypeEnum.PARTIAL,
            ...     reason_for_refund="Customer requested partial refund",
            ...     refund_amount=250000  # 2500 NGN
            ... )
            >>> response = await service.initiate_refund(request)
            >>> print(response.data['refund_reference'])
        """
        payload = {
            "gateway_transaction_ref": request.gateway_transaction_ref,
            "transaction_ref": request.transaction_ref,
            "refund_type": request.refund_type.value,
            "reason_for_refund": request.reason_for_refund,
        }

        # Add refund amount for partial refunds
        if request.refund_amount is not None:
            payload["refund_amount"] = str(request.refund_amount)

        refund_type_str = request.refund_type.value.lower()
        logger.info(
            f"Initiating {refund_type_str} refund for transaction {request.transaction_ref}. "
            f"Reason: {request.reason_for_refund}"
        )

        response_data = await self.client.post("/transaction/refund", data=payload)

        refund_ref = response_data.get("data", {}).get("refund_reference", "N/A")
        logger.info(f"Refund initiated successfully. Reference: {refund_ref}")

        return InitiateRefundResponse(
            status=response_data.get("status", 200),
            success=response_data.get("success", False),
            message=response_data.get("message", ""),
            data=response_data.get("data", {}),
        )

    async def get_refund_status(self, refund_reference: str) -> dict[str, Any]:
        """
        Get the status of a refund.

        Query the current status of a previously initiated refund.

        Args:
            refund_reference: Refund reference from initiate_refund response

        Returns:
            Dictionary with refund status details

        Raises:
            SquadAuthenticationError: If API authentication fails
            SquadNotFoundError: If refund not found
            SquadRequestError: If API request fails

        Example:
            >>> status = await service.get_refund_status("REFUND-SQOKOY1708696818297_1_1")
            >>> print(status.get('refund_status'))
            'completed'
        """
        logger.info(f"Fetching refund status for {refund_reference}")

        # Note: Squad API may not have a dedicated GET refund endpoint.
        # This is a placeholder for future implementation if Squad adds it.
        # For now, tracking can be done via transaction verification.

        logger.warning(
            "get_refund_status: Squad API doesn't provide dedicated refund status endpoint. "
            "Use transaction verification instead."
        )

        return {
            "warning": "Refund status must be tracked via transaction verification",
            "refund_reference": refund_reference,
        }
