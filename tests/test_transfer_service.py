"""
Unit tests for Transfer Service.

Tests all transfer operations: account lookup, initiate, requery, and list transfers.
"""

import pytest
from unittest.mock import AsyncMock

from app.models.schemas import (
    AccountLookupRequest,
    InitiateTransferRequest,
    RequeryTransferRequest,
    GetAllTransfersRequest,
)
from app.services.transfer_service import TransferService
from app.utils.exceptions import SquadNotFoundError


class TestAccountLookup:
    """Tests for account lookup operations."""

    @pytest.mark.asyncio
    async def test_lookup_account_success(
        self,
        transfer_service: TransferService,
        mock_squad_client: AsyncMock,
        sample_account_lookup_payload: dict,
    ):
        """Test successful account lookup."""
        mock_squad_client.post.return_value = sample_account_lookup_payload

        request = AccountLookupRequest(
            bank_code="000013",  # GTBank
            account_number="0933384111",
        )

        response = await transfer_service.lookup_account(request)

        assert response.status == 200
        assert response.success is True
        assert response.data["account_name"] == "JOHN CHRISTIAN DOE"
        assert response.data["account_number"] == "0933384111"
        mock_squad_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_lookup_account_invalid_number(
        self,
        transfer_service: TransferService,
        mock_squad_client: AsyncMock,
    ):
        """Test lookup with invalid account number."""
        mock_squad_client.post.side_effect = SquadNotFoundError(
            message="Account not found",
            status_code=404,
        )

        request = AccountLookupRequest(
            bank_code="000013",
            account_number="9999999999",
        )

        with pytest.raises(SquadNotFoundError):
            await transfer_service.lookup_account(request)


class TestInitiateTransfer:
    """Tests for fund transfer initiation."""

    @pytest.mark.asyncio
    async def test_initiate_transfer_success(
        self,
        transfer_service: TransferService,
        mock_squad_client: AsyncMock,
        sample_transfer_payload: dict,
        merchant_id: str,
    ):
        """Test successful transfer initiation."""
        mock_squad_client.post.return_value = sample_transfer_payload

        request = InitiateTransferRequest(
            transaction_reference="TRANSFER_001",
            amount=500000,  # 5000 NGN
            bank_code="000013",  # GTBank
            account_number="0933384111",
            account_name="JOHN CHRISTIAN DOE",
            currency_id="NGN",
            remark="Payment for invoice #001",
        )

        response = await transfer_service.initiate_transfer(request, merchant_id)

        assert response.status == 200
        assert response.success is True
        assert "nip_transaction_reference" in response.data
        
        # Verify merchant ID was prepended
        call_args = mock_squad_client.post.call_args
        assert merchant_id in call_args[1]["data"]["transaction_reference"]

    @pytest.mark.asyncio
    async def test_initiate_transfer_with_merchant_id_prefix(
        self,
        transfer_service: TransferService,
        mock_squad_client: AsyncMock,
        sample_transfer_payload: dict,
        merchant_id: str,
    ):
        """Test transfer with pre-existing merchant ID prefix."""
        mock_squad_client.post.return_value = sample_transfer_payload

        ref_with_prefix = f"{merchant_id}_TRANSFER_001"
        request = InitiateTransferRequest(
            transaction_reference=ref_with_prefix,
            amount=500000,
            bank_code="000013",
            account_number="0933384111",
            account_name="JOHN CHRISTIAN DOE",
            currency_id="NGN",
            remark="Payment",
        )

        response = await transfer_service.initiate_transfer(request, merchant_id)

        # Should not double-prefix
        call_args = mock_squad_client.post.call_args
        tx_ref = call_args[1]["data"]["transaction_reference"]
        assert tx_ref == ref_with_prefix
        assert tx_ref.count(merchant_id) == 1


class TestRequeryTransfer:
    """Tests for transfer status requery."""

    @pytest.mark.asyncio
    async def test_requery_transfer_success(
        self,
        transfer_service: TransferService,
        mock_squad_client: AsyncMock,
    ):
        """Test successful transfer requery."""
        payload = {
            "status": 200,
            "success": True,
            "message": "Success",
            "data": {
                "transaction_reference": "MERCHANT_TRANSFER_001",
                "transaction_status": "success",
                "amount": "500000",
                "account_number": "0933384111",
            },
        }
        mock_squad_client.post.return_value = payload

        request = RequeryTransferRequest(transaction_reference="MERCHANT_TRANSFER_001")
        response = await transfer_service.requery_transfer(request)

        assert response.status == 200
        assert response.success is True
        assert response.data["transaction_status"] == "success"

    @pytest.mark.asyncio
    async def test_requery_transfer_timeout(
        self,
        transfer_service: TransferService,
        mock_squad_client: AsyncMock,
    ):
        """Test requery of transfer that timed out initially."""
        payload = {
            "status": 200,
            "success": True,
            "message": "Success",
            "data": {
                "transaction_reference": "MERCHANT_TRANSFER_001",
                "transaction_status": "success",  # Eventually succeeded
            },
        }
        mock_squad_client.post.return_value = payload

        request = RequeryTransferRequest(transaction_reference="MERCHANT_TRANSFER_001")
        response = await transfer_service.requery_transfer(request)

        # Confirm original 424 timeout resolved
        assert response.data["transaction_status"] == "success"


class TestGetAllTransfers:
    """Tests for retrieving transfer list."""

    @pytest.mark.asyncio
    async def test_get_all_transfers_success(
        self,
        transfer_service: TransferService,
        mock_squad_client: AsyncMock,
    ):
        """Test successful retrieval of all transfers."""
        payload = {
            "status": 200,
            "success": True,
            "message": "Success",
            "data": [
                {
                    "account_number_credited": "0933384111",
                    "amount_debited": "500000",
                    "success": True,
                    "transaction_status": "success",
                },
                {
                    "account_number_credited": "0123456789",
                    "amount_debited": "1000000",
                    "success": True,
                    "transaction_status": "success",
                },
            ],
        }
        mock_squad_client.get.return_value = payload

        request = GetAllTransfersRequest(page=1, per_page=20, sort_dir="DESC")
        response = await transfer_service.get_all_transfers(request)

        assert response.status == 200
        assert response.success is True
        assert len(response.data) == 2
        mock_squad_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_transfers_pagination(
        self,
        transfer_service: TransferService,
        mock_squad_client: AsyncMock,
    ):
        """Test pagination of transfer list."""
        payload = {"status": 200, "success": True, "data": []}
        mock_squad_client.get.return_value = payload

        request = GetAllTransfersRequest(page=3, per_page=50, sort_dir="ASC")
        response = await transfer_service.get_all_transfers(request)

        call_args = mock_squad_client.get.call_args
        params = call_args[1]["params"]
        assert params["page"] == 3
        assert params["perPage"] == 50
        assert params["dir"] == "ASC"


class TestTransferErrorHandling:
    """Tests for error handling in transfer operations."""

    @pytest.mark.asyncio
    async def test_lookup_account_invalid_bank_code(
        self,
        transfer_service: TransferService,
        mock_squad_client: AsyncMock,
    ):
        """Test lookup with invalid bank code."""
        from app.utils.exceptions import SquadValidationError
        
        mock_squad_client.post.side_effect = SquadValidationError(
            message="Invalid bank code",
            status_code=400,
        )

        request = AccountLookupRequest(
            bank_code="999999",
            account_number="0933384111",
        )

        with pytest.raises(SquadValidationError):
            await transfer_service.lookup_account(request)
