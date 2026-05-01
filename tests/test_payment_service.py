"""
Unit tests for Payment Service.

Tests all payment operations: initiate, verify, charge card, cancel recurring,
query transactions, and simulate payments.
"""

import pytest
from unittest.mock import AsyncMock

from app.models.schemas import (
    InitiatePaymentRequest,
    VerifyPaymentRequest,
    ChargeCardRequest,
    CancelRecurringRequest,
    QueryTransactionsRequest,
    CurrencyEnum,
    PaymentChannelEnum,
)
from app.services.payment_service import PaymentService
from app.utils.exceptions import SquadValidationError, SquadRequestError


class TestInitiatePayment:
    """Tests for payment initiation."""

    @pytest.mark.asyncio
    async def test_initiate_payment_success(
        self,
        payment_service: PaymentService,
        mock_squad_client: AsyncMock,
        sample_payment_payload: dict,
    ):
        """Test successful payment initiation."""
        mock_squad_client.post.return_value = sample_payment_payload

        request = InitiatePaymentRequest(
            amount=50000,
            email="customer@example.com",
            customer_name="John Doe",
        )

        response = await payment_service.initiate_payment(request)

        assert response.status == 200
        assert response.message == "success"
        assert "checkout_url" in response.data
        assert response.data["transaction_ref"] == "TXN_20250330_001"
        mock_squad_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_initiate_payment_with_all_channels(
        self,
        payment_service: PaymentService,
        mock_squad_client: AsyncMock,
        sample_payment_payload: dict,
    ):
        """Test payment initiation with all payment channels."""
        mock_squad_client.post.return_value = sample_payment_payload

        request = InitiatePaymentRequest(
            amount=100000,
            email="test@example.com",
            payment_channels=[
                PaymentChannelEnum.CARD,
                PaymentChannelEnum.TRANSFER,
                PaymentChannelEnum.USSD,
                PaymentChannelEnum.BANK,
            ],
            currency=CurrencyEnum.NGN,
        )

        response = await payment_service.initiate_payment(request)

        assert response.status == 200
        call_args = mock_squad_client.post.call_args
        assert call_args[1]["data"]["payment_channels"] == ["card", "transfer", "ussd", "bank"]

    @pytest.mark.asyncio
    async def test_initiate_recurring_payment(
        self,
        payment_service: PaymentService,
        mock_squad_client: AsyncMock,
        sample_payment_payload: dict,
    ):
        """Test recurring payment initiation with card tokenization."""
        mock_squad_client.post.return_value = sample_payment_payload

        request = InitiatePaymentRequest(
            amount=50000,
            email="customer@example.com",
            is_recurring=True,
        )

        response = await payment_service.initiate_payment(request)

        assert response.status == 200
        call_args = mock_squad_client.post.call_args
        assert call_args[1]["data"]["is_recurring"] is True

    @pytest.mark.asyncio
    async def test_initiate_payment_with_metadata(
        self,
        payment_service: PaymentService,
        mock_squad_client: AsyncMock,
        sample_payment_payload: dict,
    ):
        """Test payment initiation with custom metadata."""
        mock_squad_client.post.return_value = sample_payment_payload

        metadata = {"order_id": "ORDER_123", "customer_type": "premium"}

        request = InitiatePaymentRequest(
            amount=50000,
            email="customer@example.com",
            metadata=metadata,
        )

        response = await payment_service.initiate_payment(request)

        assert response.status == 200
        call_args = mock_squad_client.post.call_args
        assert call_args[1]["data"]["metadata"] == metadata


class TestVerifyPayment:
    """Tests for payment verification."""

    @pytest.mark.asyncio
    async def test_verify_payment_success(
        self,
        payment_service: PaymentService,
        mock_squad_client: AsyncMock,
        sample_payment_verification_payload: dict,
    ):
        """Test successful payment verification."""
        mock_squad_client.get.return_value = sample_payment_verification_payload

        request = VerifyPaymentRequest(transaction_ref="TXN_20250330_001")
        response = await payment_service.verify_payment(request)

        assert response.status == 200
        assert response.success is True
        assert response.data["transaction_status"] == "success"
        mock_squad_client.get.assert_called_once_with("/transaction/verify/TXN_20250330_001")

    @pytest.mark.asyncio
    async def test_verify_payment_pending(
        self,
        payment_service: PaymentService,
        mock_squad_client: AsyncMock,
    ):
        """Test verification of pending payment."""
        payload = {
            "status": 200,
            "success": True,
            "data": {
                "transaction_status": "pending",
                "transaction_ref": "TXN_PENDING",
            },
        }
        mock_squad_client.get.return_value = payload

        request = VerifyPaymentRequest(transaction_ref="TXN_PENDING")
        response = await payment_service.verify_payment(request)

        assert response.data["transaction_status"] == "pending"


class TestChargeCard:
    """Tests for card charging (recurring payments)."""

    @pytest.mark.asyncio
    async def test_charge_card_success(
        self,
        payment_service: PaymentService,
        mock_squad_client: AsyncMock,
        sample_charge_card_payload: dict,
    ):
        """Test successful card charge."""
        mock_squad_client.post.return_value = sample_charge_card_payload

        request = ChargeCardRequest(
            amount=25000,
            token_id="AUTH_token123",
        )

        response = await payment_service.charge_card(request)

        assert response.status == 200
        assert response.success is True
        assert response.data["transaction_status"] == "success"
        mock_squad_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_charge_card_with_custom_reference(
        self,
        payment_service: PaymentService,
        mock_squad_client: AsyncMock,
        sample_charge_card_payload: dict,
    ):
        """Test card charge with custom transaction reference."""
        mock_squad_client.post.return_value = sample_charge_card_payload

        request = ChargeCardRequest(
            amount=25000,
            token_id="AUTH_token123",
            transaction_ref="CUSTOM_REF_001",
        )

        response = await payment_service.charge_card(request)

        assert response.success is True
        call_args = mock_squad_client.post.call_args
        assert call_args[1]["data"]["transaction_ref"] == "CUSTOM_REF_001"


class TestCancelRecurring:
    """Tests for cancelling recurring payments."""

    @pytest.mark.asyncio
    async def test_cancel_recurring_success(
        self,
        payment_service: PaymentService,
        mock_squad_client: AsyncMock,
    ):
        """Test successful recurring payment cancellation."""
        payload = {
            "status": 200,
            "success": True,
            "message": "Success",
            "data": {
                "auth_code": ["AUTH_token123"],
            },
        }
        mock_squad_client.patch.return_value = payload

        request = CancelRecurringRequest(auth_code=["AUTH_token123"])
        response = await payment_service.cancel_recurring(request)

        assert response.status == 200
        assert response.success is True
        mock_squad_client.patch.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_multiple_recurring(
        self,
        payment_service: PaymentService,
        mock_squad_client: AsyncMock,
    ):
        """Test cancelling multiple recurring payment authorizations."""
        payload = {
            "status": 200,
            "success": True,
            "message": "Success",
            "data": {
                "auth_code": ["AUTH_token1", "AUTH_token2", "AUTH_token3"],
            },
        }
        mock_squad_client.patch.return_value = payload

        request = CancelRecurringRequest(
            auth_code=["AUTH_token1", "AUTH_token2", "AUTH_token3"]
        )
        response = await payment_service.cancel_recurring(request)

        assert response.success is True
        call_args = mock_squad_client.patch.call_args
        assert len(call_args[1]["data"]["auth_code"]) == 3


class TestQueryTransactions:
    """Tests for querying transactions."""

    @pytest.mark.asyncio
    async def test_query_transactions_success(
        self,
        payment_service: PaymentService,
        mock_squad_client: AsyncMock,
        sample_dates: dict,
    ):
        """Test successful transaction query."""
        payload = {
            "status": 200,
            "success": True,
            "message": "Success",
            "data": [
                {
                    "transaction_ref": "TXN_001",
                    "amount": 50000,
                    "status": "success",
                    "email": "customer@example.com",
                },
                {
                    "transaction_ref": "TXN_002",
                    "amount": 100000,
                    "status": "success",
                    "email": "another@example.com",
                },
            ],
        }
        mock_squad_client.get.return_value = payload

        request = QueryTransactionsRequest(
            start_date=sample_dates["start_date"],
            end_date=sample_dates["end_date"],
        )

        response = await payment_service.query_transactions(request)

        assert response.status == 200
        assert response.success is True
        assert len(response.data) == 2
        mock_squad_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_transactions_with_filters(
        self,
        payment_service: PaymentService,
        mock_squad_client: AsyncMock,
        sample_dates: dict,
    ):
        """Test transaction query with filters."""
        payload = {"status": 200, "success": True, "data": []}
        mock_squad_client.get.return_value = payload

        request = QueryTransactionsRequest(
            start_date=sample_dates["start_date"],
            end_date=sample_dates["end_date"],
            currency=CurrencyEnum.USD,
            reference="TXN_123",
            page=2,
            perpage=50,
        )

        response = await payment_service.query_transactions(request)

        call_args = mock_squad_client.get.call_args
        params = call_args[1]["params"]
        assert params["currency"] == "USD"
        assert params["reference"] == "TXN_123"
        assert params["page"] == 2
        assert params["perpage"] == 50


class TestSimulatePayment:
    """Tests for payment simulation (sandbox)."""

    @pytest.mark.asyncio
    async def test_simulate_payment_success(
        self,
        payment_service: PaymentService,
        mock_squad_client: AsyncMock,
    ):
        """Test successful payment simulation."""
        payload = {
            "status": 200,
            "success": True,
            "message": "Success",
            "data": "Payment successful",
        }
        mock_squad_client.post.return_value = payload

        result = await payment_service.simulate_payment(
            virtual_account_number="4879261135",
            amount=20000,
        )

        assert result["success"] is True
        call_args = mock_squad_client.post.call_args
        assert call_args[1]["data"]["virtual_account_number"] == "4879261135"
        assert call_args[1]["data"]["amount"] == "20000"


class TestPaymentErrorHandling:
    """Tests for error handling in payment operations."""

    @pytest.mark.asyncio
    async def test_initiate_payment_authentication_error(
        self,
        payment_service: PaymentService,
        mock_squad_client: AsyncMock,
    ):
        """Test authentication error during payment initiation."""
        mock_squad_client.post.side_effect = SquadValidationError(
            message="Invalid API key",
            status_code=401,
        )

        request = InitiatePaymentRequest(
            amount=50000,
            email="customer@example.com",
        )

        with pytest.raises(SquadValidationError):
            await payment_service.initiate_payment(request)

    @pytest.mark.asyncio
    async def test_charge_card_network_error(
        self,
        payment_service: PaymentService,
        mock_squad_client: AsyncMock,
    ):
        """Test network error during card charge."""
        mock_squad_client.post.side_effect = SquadRequestError(
            message="Network timeout",
        )

        request = ChargeCardRequest(
            amount=25000,
            token_id="AUTH_token123",
        )

        with pytest.raises(SquadRequestError):
            await payment_service.charge_card(request)
