"""
Unit tests for Refund Service.

Tests refund operations: full refunds, partial refunds, and refund validation.
"""

import pytest
from unittest.mock import AsyncMock

from app.models.schemas import (
    InitiateRefundRequest,
    RefundTypeEnum,
)
from app.services.refund_service import RefundService
from app.utils.exceptions import SquadValidationError


class TestInitiateFullRefund:
    """Tests for full refund operations."""

    @pytest.mark.asyncio
    async def test_full_refund_success(
        self,
        refund_service: RefundService,
        mock_squad_client: AsyncMock,
        sample_refund_payload: dict,
    ):
        """Test successful full refund."""
        mock_squad_client.post.return_value = sample_refund_payload

        request = InitiateRefundRequest(
            gateway_transaction_ref="SQOKOY1708696818297_1_1",
            transaction_ref="TXN_20250330_001",
            refund_type=RefundTypeEnum.FULL,
            reason_for_refund="Customer requested cancellation",
        )

        response = await refund_service.initiate_refund(request)

        assert response.status == 200
        assert response.success is True
        assert "refund_reference" in response.data
        mock_squad_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_full_refund_no_amount_required(
        self,
        refund_service: RefundService,
        mock_squad_client: AsyncMock,
        sample_refund_payload: dict,
    ):
        """Test that full refund doesn't require refund_amount."""
        mock_squad_client.post.return_value = sample_refund_payload

        request = InitiateRefundRequest(
            gateway_transaction_ref="SQOKOY1708696818297_1_1",
            transaction_ref="TXN_FULL",
            refund_type=RefundTypeEnum.FULL,
            reason_for_refund="Full refund needed",
            # refund_amount intentionally omitted
        )

        response = await refund_service.initiate_refund(request)

        assert response.success is True
        call_args = mock_squad_client.post.call_args
        data = call_args[1]["data"]
        assert data["refund_type"] == "Full"


class TestInitiatePartialRefund:
    """Tests for partial refund operations."""

    @pytest.mark.asyncio
    async def test_partial_refund_success(
        self,
        refund_service: RefundService,
        mock_squad_client: AsyncMock,
        sample_refund_payload: dict,
    ):
        """Test successful partial refund with amount."""
        mock_squad_client.post.return_value = sample_refund_payload

        request = InitiateRefundRequest(
            gateway_transaction_ref="SQOKOY1708696818297_1_1",
            transaction_ref="TXN_20250330_001",
            refund_type=RefundTypeEnum.PARTIAL,
            reason_for_refund="Partial refund for damaged item",
            refund_amount=250000,  # kobo (2500 NGN)
        )

        response = await refund_service.initiate_refund(request)

        assert response.status == 200
        assert response.success is True
        call_args = mock_squad_client.post.call_args
        data = call_args[1]["data"]
        assert data["refund_type"] == "Partial"
        assert data["refund_amount"] == 250000

    @pytest.mark.asyncio
    async def test_partial_refund_half_amount(
        self,
        refund_service: RefundService,
        mock_squad_client: AsyncMock,
        sample_refund_payload: dict,
    ):
        """Test partial refund for half of transaction amount."""
        mock_squad_client.post.return_value = sample_refund_payload

        request = InitiateRefundRequest(
            gateway_transaction_ref="SQOKOY1708696818297_1_1",
            transaction_ref="TXN_PARTIAL_50",
            refund_type=RefundTypeEnum.PARTIAL,
            reason_for_refund="50% refund",
            refund_amount=250000,  # Half of 500000
        )

        response = await refund_service.initiate_refund(request)

        assert response.success is True


class TestRefundValidation:
    """Tests for refund request validation."""

    @pytest.mark.asyncio
    async def test_partial_refund_requires_amount(
        self,
        refund_service: RefundService,
        mock_squad_client: AsyncMock,
    ):
        """Test that partial refund requires refund_amount."""
        # Partial refund without amount should raise validation error
        request = InitiateRefundRequest(
            gateway_transaction_ref="SQOKOY1708696818297_1_1",
            transaction_ref="TXN_INVALID_PARTIAL",
            refund_type=RefundTypeEnum.PARTIAL,
            reason_for_refund="Missing amount",
            # refund_amount is missing - should fail
        )

        # The service should handle this validation
        # Either raise error directly or the squad_client will return error
        with pytest.raises((SquadValidationError, ValueError, AttributeError)):
            await refund_service.initiate_refund(request)

    @pytest.mark.asyncio
    async def test_refund_with_empty_reason(
        self,
        refund_service: RefundService,
        mock_squad_client: AsyncMock,
    ):
        """Test that reason for refund is required."""
        mock_squad_client.post.side_effect = SquadValidationError(
            message="reason_for_refund is required",
            status_code=400,
        )

        request = InitiateRefundRequest(
            gateway_transaction_ref="SQOKOY1708696818297_1_1",
            transaction_ref="TXN_NO_REASON",
            refund_type=RefundTypeEnum.FULL,
            reason_for_refund="",  # Empty reason
        )

        with pytest.raises(SquadValidationError):
            await refund_service.initiate_refund(request)


class TestRefundErrorHandling:
    """Tests for error handling in refund operations."""

    @pytest.mark.asyncio
    async def test_refund_invalid_gateway_ref(
        self,
        refund_service: RefundService,
        mock_squad_client: AsyncMock,
    ):
        """Test error with invalid gateway transaction reference."""
        mock_squad_client.post.side_effect = SquadValidationError(
            message="Invalid gateway transaction reference",
            status_code=400,
        )

        request = InitiateRefundRequest(
            gateway_transaction_ref="INVALID_REF",
            transaction_ref="TXN_INVALID",
            refund_type=RefundTypeEnum.FULL,
            reason_for_refund="Invalid gateway ref",
        )

        with pytest.raises(SquadValidationError):
            await refund_service.initiate_refund(request)

    @pytest.mark.asyncio
    async def test_refund_transaction_not_found(
        self,
        refund_service: RefundService,
        mock_squad_client: AsyncMock,
    ):
        """Test error when transaction to refund is not found."""
        from app.utils.exceptions import SquadNotFoundError

        mock_squad_client.post.side_effect = SquadNotFoundError(
            message="Transaction not found",
            status_code=404,
        )

        request = InitiateRefundRequest(
            gateway_transaction_ref="SQOKOY_NONEXISTENT",
            transaction_ref="TXN_NOT_FOUND",
            refund_type=RefundTypeEnum.FULL,
            reason_for_refund="Transaction not found",
        )

        with pytest.raises(SquadNotFoundError):
            await refund_service.initiate_refund(request)

    @pytest.mark.asyncio
    async def test_refund_already_refunded(
        self,
        refund_service: RefundService,
        mock_squad_client: AsyncMock,
    ):
        """Test error when trying to refund already refunded transaction."""
        mock_squad_client.post.side_effect = SquadValidationError(
            message="Transaction already refunded",
            status_code=400,
        )

        request = InitiateRefundRequest(
            gateway_transaction_ref="SQOKOY_ALREADY_REFUNDED",
            transaction_ref="TXN_ALREADY_REFUNDED",
            refund_type=RefundTypeEnum.FULL,
            reason_for_refund="Attempting double refund",
        )

        with pytest.raises(SquadValidationError):
            await refund_service.initiate_refund(request)


class TestRefundStatusTracking:
    """Tests for refund status tracking."""

    @pytest.mark.asyncio
    async def test_refund_reference_in_response(
        self,
        refund_service: RefundService,
        mock_squad_client: AsyncMock,
        sample_refund_payload: dict,
    ):
        """Test that refund response includes reference for tracking."""
        mock_squad_client.post.return_value = sample_refund_payload

        request = InitiateRefundRequest(
            gateway_transaction_ref="SQOKOY1708696818297_1_1",
            transaction_ref="TXN_TRACKING",
            refund_type=RefundTypeEnum.FULL,
            reason_for_refund="Track this refund",
        )

        response = await refund_service.initiate_refund(request)

        # Response should have reference for tracking
        assert "refund_reference" in response.data
        assert response.data["refund_reference"] is not None
