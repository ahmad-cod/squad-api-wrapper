"""
Unit tests for Virtual Account Service.

Tests all virtual account operations: pool creation, transaction initiation,
requery, updates, and payment simulation.
"""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timedelta

from app.models.schemas import (
    CreateVAPoolRequest,
    InitiateVATransactionRequest,
    RequeryVATransactionRequest,
    UpdateVATransactionRequest,
)
from app.services.virtual_account_service import VirtualAccountService
from app.utils.exceptions import SquadValidationError


class TestCreateVAPool:
    """Tests for virtual account pool creation."""

    @pytest.mark.asyncio
    async def test_create_pool_with_beneficiary(
        self,
        va_service: VirtualAccountService,
        mock_squad_client: AsyncMock,
    ):
        """Test pool creation with beneficiary account."""
        payload = {
            "status": 200,
            "success": True,
            "message": "Virtual account pool created",
            "data": {
                "pool_reference": "POOL_REF_12345",
                "account_name": "Acme Store",
            },
        }
        mock_squad_client.post.return_value = payload

        request = CreateVAPoolRequest(
            beneficiary_account="0147799000",
            first_name="Acme",
            last_name="Store",
        )

        response = await va_service.create_va_pool(request)

        assert response.status == 200
        assert response.success is True
        mock_squad_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_pool_defaults_names(
        self,
        va_service: VirtualAccountService,
        mock_squad_client: AsyncMock,
    ):
        """Test pool creation with default account names."""
        payload = {
            "status": 200,
            "success": True,
            "data": {"pool_reference": "POOL_REF_12345"},
        }
        mock_squad_client.post.return_value = payload

        request = CreateVAPoolRequest()

        response = await va_service.create_va_pool(request)

        assert response.success is True
        call_args = mock_squad_client.post.call_args
        # Should use default first/last names
        data = call_args[1]["data"]
        assert "first_name" in data


class TestInitiateVATransaction:
    """Tests for virtual account transaction initiation."""

    @pytest.mark.asyncio
    async def test_initiate_va_transaction_success(
        self,
        va_service: VirtualAccountService,
        mock_squad_client: AsyncMock,
        sample_va_initiate_payload: dict,
    ):
        """Test successful VA transaction initiation."""
        mock_squad_client.post.return_value = sample_va_initiate_payload

        request = InitiateVATransactionRequest(
            amount=100000,
            duration=600,
            email="customer@example.com",
            transaction_ref="TXN_20250330_001",
        )

        response = await va_service.initiate_va_transaction(request)

        assert response.status == 200
        assert response.success is True
        assert response.data["account_number"] == "4879261135"
        assert "expires_at" in response.data
        mock_squad_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_initiate_va_transaction_kobo_conversion(
        self,
        va_service: VirtualAccountService,
        mock_squad_client: AsyncMock,
        sample_va_initiate_payload: dict,
    ):
        """Test that kobo amounts are properly converted to naira."""
        mock_squad_client.post.return_value = sample_va_initiate_payload

        request = InitiateVATransactionRequest(
            amount=100000,  # 1000 naira in kobo
            duration=300,
            email="test@example.com",
            transaction_ref="TXN_TEST",
        )

        response = await va_service.initiate_va_transaction(request)

        assert response.success is True
        call_args = mock_squad_client.post.call_args
        # Amount should be converted to naira (kobo/100)
        sent_data = call_args[1]["data"]
        assert sent_data["amount"] == "1000.00"


class TestRequeryVATransaction:
    """Tests for virtual account transaction requery."""

    @pytest.mark.asyncio
    async def test_requery_va_success(
        self,
        va_service: VirtualAccountService,
        mock_squad_client: AsyncMock,
        sample_va_requery_payload: dict,
    ):
        """Test successful VA transaction requery."""
        mock_squad_client.get.return_value = sample_va_requery_payload

        request = RequeryVATransactionRequest(transaction_ref="TXN_20250330_001")
        response = await va_service.requery_va_transaction(request)

        assert response.status == 200
        assert response.success is True
        assert "count" in response.data
        mock_squad_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_requery_va_multiple_attempts(
        self,
        va_service: VirtualAccountService,
        mock_squad_client: AsyncMock,
    ):
        """Test requery returns multiple transaction attempts."""
        payload = {
            "status": 200,
            "success": True,
            "data": {
                "count": 3,
                "rows": [
                    {
                        "transaction_status": "SUCCESS",
                        "amount_received": "1000.00",
                    },
                    {
                        "transaction_status": "EXPIRED",
                        "reason": "Payment not received",
                    },
                    {
                        "transaction_status": "MISMATCH",
                        "amount_received": "1500.00",
                    },
                ],
            },
        }
        mock_squad_client.get.return_value = payload

        request = RequeryVATransactionRequest(transaction_ref="TXN_MULTI")
        response = await va_service.requery_va_transaction(request)

        assert response.data["count"] == 3
        assert response.data["rows"][0]["transaction_status"] == "SUCCESS"
        assert response.data["rows"][1]["transaction_status"] == "EXPIRED"
        assert response.data["rows"][2]["transaction_status"] == "MISMATCH"


class TestUpdateVATransaction:
    """Tests for updating VA transaction amount/duration."""

    @pytest.mark.asyncio
    async def test_update_va_amount(
        self,
        va_service: VirtualAccountService,
        mock_squad_client: AsyncMock,
    ):
        """Test updating VA transaction amount."""
        payload = {
            "status": 200,
            "success": True,
            "data": {
                "transaction_reference": "TXN_UPDATE",
                "amount": "1500.00",
            },
        }
        mock_squad_client.patch.return_value = payload

        request = UpdateVATransactionRequest(
            transaction_reference="TXN_UPDATE",
            amount=150000,  # kobo
        )

        response = await va_service.update_va_amount_duration(request)

        assert response.success is True
        call_args = mock_squad_client.patch.call_args
        # Amount should be converted to naira
        assert call_args[1]["data"]["amount"] == "1500.00"

    @pytest.mark.asyncio
    async def test_update_va_duration(
        self,
        va_service: VirtualAccountService,
        mock_squad_client: AsyncMock,
    ):
        """Test updating VA transaction duration."""
        payload = {
            "status": 200,
            "success": True,
            "data": {"duration": 900},
        }
        mock_squad_client.patch.return_value = payload

        request = UpdateVATransactionRequest(
            transaction_reference="TXN_DUR",
            duration=900,
        )

        response = await va_service.update_va_amount_duration(request)

        assert response.success is True

    @pytest.mark.asyncio
    async def test_update_va_both_amount_and_duration(
        self,
        va_service: VirtualAccountService,
        mock_squad_client: AsyncMock,
    ):
        """Test updating both VA amount and duration."""
        payload = {
            "status": 200,
            "success": True,
            "data": {
                "amount": "2000.00",
                "duration": 1200,
            },
        }
        mock_squad_client.patch.return_value = payload

        request = UpdateVATransactionRequest(
            transaction_reference="TXN_BOTH",
            amount=200000,
            duration=1200,
        )

        response = await va_service.update_va_amount_duration(request)

        assert response.success is True
        call_args = mock_squad_client.patch.call_args
        data = call_args[1]["data"]
        assert "amount" in data
        assert "duration" in data


class TestSimulateVAPayment:
    """Tests for simulating VA payments (sandbox)."""

    @pytest.mark.asyncio
    async def test_simulate_va_payment_success(
        self,
        va_service: VirtualAccountService,
        mock_squad_client: AsyncMock,
    ):
        """Test successful VA payment simulation."""
        payload = {
            "status": 200,
            "success": True,
            "message": "Success",
            "data": "Payment simulation successful",
        }
        mock_squad_client.post.return_value = payload

        result = await va_service.simulate_va_payment(
            virtual_account_number="4879261135",
            amount_in_naira=1000,
        )

        assert result["success"] is True
        call_args = mock_squad_client.post.call_args
        assert call_args[1]["data"]["virtual_account_number"] == "4879261135"
        assert call_args[1]["data"]["amount"] == "1000"


class TestVirtualAccountErrorHandling:
    """Tests for error handling in VA operations."""

    @pytest.mark.asyncio
    async def test_create_pool_invalid_account(
        self,
        va_service: VirtualAccountService,
        mock_squad_client: AsyncMock,
    ):
        """Test error when creating pool with invalid beneficiary account."""
        mock_squad_client.post.side_effect = SquadValidationError(
            message="Invalid beneficiary account",
            status_code=400,
        )

        request = CreateVAPoolRequest(
            beneficiary_account="INVALID",
        )

        with pytest.raises(SquadValidationError):
            await va_service.create_va_pool(request)

    @pytest.mark.asyncio
    async def test_initiate_va_invalid_duration(
        self,
        va_service: VirtualAccountService,
        mock_squad_client: AsyncMock,
    ):
        """Test error with invalid duration."""
        mock_squad_client.post.side_effect = SquadValidationError(
            message="Duration must be between 60 and 86400 seconds",
            status_code=400,
        )

        request = InitiateVATransactionRequest(
            amount=100000,
            duration=30,  # Too short
            email="customer@example.com",
            transaction_ref="TXN_INVALID",
        )

        with pytest.raises(SquadValidationError):
            await va_service.initiate_va_transaction(request)
