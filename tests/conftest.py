"""
Pytest configuration and shared fixtures for Squad API tests.

Provides mock client, sample payloads, and utility fixtures for all tests.
"""

import json
from datetime import datetime, timedelta
from typing import Any, AsyncGenerator

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, Mock

from app.utils.squad_client import SquadAPIClient
from app.services.payment_service import PaymentService
from app.services.transfer_service import TransferService
from app.services.refund_service import RefundService
from app.services.virtual_account_service import VirtualAccountService
from app.services.webhook_service import WebhookService


# ============================================================================
# FIXTURES: CONFIGURATION
# ============================================================================


@pytest.fixture
def squad_secret_key() -> str:
    """Squad API secret key for testing."""
    return "sandbox_sk_test_1234567890abcdef"


@pytest.fixture
def squad_base_url() -> str:
    """Squad API base URL for testing (sandbox)."""
    return "https://sandbox-api-d.squadco.com"


@pytest.fixture
def merchant_id() -> str:
    """Merchant ID for testing."""
    return "TEST_MERCHANT_001"


# ============================================================================
# FIXTURES: API CLIENT
# ============================================================================


@pytest.fixture
def mock_squad_client(squad_secret_key: str, squad_base_url: str) -> AsyncMock:
    """Mock SquadAPIClient for testing."""
    client = AsyncMock(spec=SquadAPIClient)
    client.secret_key = squad_secret_key
    client.base_url = squad_base_url
    return client


# ============================================================================
# FIXTURES: SERVICES
# ============================================================================


@pytest.fixture
def payment_service(mock_squad_client: AsyncMock) -> PaymentService:
    """PaymentService with mocked client."""
    return PaymentService(client=mock_squad_client)


@pytest.fixture
def transfer_service(mock_squad_client: AsyncMock) -> TransferService:
    """TransferService with mocked client."""
    return TransferService(client=mock_squad_client)


@pytest.fixture
def refund_service(mock_squad_client: AsyncMock) -> RefundService:
    """RefundService with mocked client."""
    return RefundService(client=mock_squad_client)


@pytest.fixture
def va_service(mock_squad_client: AsyncMock) -> VirtualAccountService:
    """VirtualAccountService with mocked client."""
    return VirtualAccountService(client=mock_squad_client)


@pytest.fixture
def webhook_service(squad_secret_key: str) -> WebhookService:
    """WebhookService with test secret key."""
    return WebhookService(secret_key=squad_secret_key)


# ============================================================================
# FIXTURES: SAMPLE PAYLOADS
# ============================================================================


@pytest.fixture
def sample_payment_payload() -> dict[str, Any]:
    """Sample payment initiation response from Squad."""
    return {
        "status": 200,
        "message": "success",
        "data": {
            "checkout_url": "https://sandbox-pay.squadco.com/txn_123456",
            "transaction_ref": "TXN_20250330_001",
            "transaction_amount": 50000,
            "authorized_channels": ["card", "ussd", "transfer", "bank"],
            "currency": "NGN",
        },
    }


@pytest.fixture
def sample_payment_verification_payload() -> dict[str, Any]:
    """Sample payment verification response from Squad."""
    return {
        "status": 200,
        "success": True,
        "message": "success",
        "data": {
            "transaction_ref": "TXN_20250330_001",
            "transaction_status": "success",
            "amount": 50000,
            "email": "customer@example.com",
            "currency": "NGN",
        },
    }


@pytest.fixture
def sample_charge_card_payload() -> dict[str, Any]:
    """Sample card charge response from Squad."""
    return {
        "status": 200,
        "success": True,
        "message": "Success",
        "data": {
            "transaction_ref": "CHARGE_20250330_001",
            "transaction_status": "success",
            "amount": 25000,
        },
    }


@pytest.fixture
def sample_account_lookup_payload() -> dict[str, Any]:
    """Sample account lookup response from Squad."""
    return {
        "status": 200,
        "success": True,
        "message": "Success",
        "data": {
            "account_name": "JOHN CHRISTIAN DOE",
            "account_number": "0933384111",
        },
    }


@pytest.fixture
def sample_transfer_payload() -> dict[str, Any]:
    """Sample transfer initiation response from Squad."""
    return {
        "status": 200,
        "success": True,
        "message": "Success",
        "data": {
            "transaction_reference": "TEST_MERCHANT_001_TRANSFER_001",
            "response_description": "Approved or completed successfully",
            "currency_id": "NGN",
            "amount": "500000",
            "nip_transaction_reference": "110059250901053503159119194486",
            "account_number": "0933384111",
            "account_name": "JOHN CHRISTIAN DOE",
            "destination_institution_name": "GTBank Plc",
        },
    }


@pytest.fixture
def sample_refund_payload() -> dict[str, Any]:
    """Sample refund initiation response from Squad."""
    return {
        "status": 200,
        "success": True,
        "message": "Success",
        "data": {
            "gateway_refund_status": "pending",
            "refund_status": 2,
            "refund_reference": "REFUND-SQOKOY1708696818297_1_1",
        },
    }


@pytest.fixture
def sample_va_initiate_payload() -> dict[str, Any]:
    """Sample VA transaction initiation response from Squad."""
    return {
        "status": 200,
        "success": True,
        "message": "Success",
        "data": {
            "is_blocked": False,
            "account_name": "SQUAD CHECKOUT",
            "account_number": "4879261135",
            "expected_amount": "1000.00",
            "expires_at": "2025-03-30T09:30:00.000Z",
            "transaction_reference": "TXN_20250330_001",
            "bank": "GTBank",
            "currency": "NGN",
        },
    }


@pytest.fixture
def sample_va_requery_payload() -> dict[str, Any]:
    """Sample VA requery response from Squad."""
    return {
        "status": 200,
        "success": True,
        "message": "Success",
        "data": {
            "count": 1,
            "rows": [
                {
                    "transaction_status": "SUCCESS",
                    "transaction_reference": "REF20250330S51557521_M01282553_0855445055",
                    "created_at": "2025-03-30T08:52:42.729Z",
                    "refund": None,
                }
            ],
        },
    }


@pytest.fixture
def sample_payment_webhook() -> dict[str, Any]:
    """Sample payment webhook payload from Squad."""
    return {
        "Event": "charge_successful",
        "TransactionRef": "TXN_20250330_001",
        "Body": {
            "amount": 50000,
            "transaction_ref": "TXN_20250330_001",
            "gateway_ref": "SQTECH6389058547434300003_1_6_1",
            "transaction_status": "success",
            "email": "customer@example.com",
            "merchant_id": "TEST_MERCHANT_001",
            "currency": "NGN",
            "transaction_type": "Card",
            "is_recurring": False,
        },
    }


@pytest.fixture
def sample_va_webhook_success() -> dict[str, Any]:
    """Sample VA SUCCESS webhook payload from Squad."""
    return {
        "transaction_status": "SUCCESS",
        "merchant_reference": "TXN_20250330_001",
        "merchant_amount": "1000.00",
        "amount_received": "1000.00",
        "transaction_reference": "REF20250330S51557521_M01282553_0855445055",
        "email": "customer@example.com",
        "merchant_id": "TEST_MERCHANT_001",
        "date": "2025-03-30T08:52:42.729Z",
        "sender_name": "JOHN CHRISTIAN DOE",
    }


@pytest.fixture
def sample_va_webhook_expired() -> dict[str, Any]:
    """Sample VA EXPIRED webhook payload from Squad."""
    return {
        "transaction_status": "EXPIRED",
        "merchant_reference": "TXN_20250330_002",
        "merchant_amount": "500.00",
        "amount_received": "0.00",
        "transaction_reference": "REF20250330S51557521_M01282553_0855445056",
        "email": "customer@example.com",
        "merchant_id": "TEST_MERCHANT_001",
        "date": "2025-03-31T08:52:42.729Z",
        "sender_name": None,
    }


# ============================================================================
# FIXTURES: UTILITIES
# ============================================================================


@pytest.fixture
def sample_dates() -> dict[str, Any]:
    """Sample start and end dates for transaction queries."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    return {
        "start_date": start_date,
        "end_date": end_date,
    }


@pytest.mark.asyncio
@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for integration tests."""
    async with AsyncClient(app=None, base_url="http://test") as client:
        yield client
