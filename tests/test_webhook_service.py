"""
Unit tests for Webhook Service.

Tests webhook signature validation and event processing.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch

from app.services.webhook_service import WebhookService
from app.utils.webhooks import compute_webhook_signature
from app.utils.exceptions import SquadWebhookError


class TestWebhookSignatureValidation:
    """Tests for webhook signature validation."""

    def test_validate_webhook_signature_success(
        self,
        webhook_service: WebhookService,
        sample_va_webhook_success: dict,
    ):
        """Test successful webhook signature validation."""
        # Compute valid signature
        valid_signature = compute_webhook_signature(
            sample_va_webhook_success,
            webhook_service.secret_key,
        )

        # Should not raise exception
        is_valid = webhook_service.validate_webhook_signature(
            payload=sample_va_webhook_success,
            received_signature=valid_signature,
        )

        assert is_valid is True

    def test_validate_webhook_signature_invalid(
        self,
        webhook_service: WebhookService,
        sample_va_webhook_success: dict,
    ):
        """Test invalid webhook signature rejection."""
        invalid_signature = "invalid_signature_hash"

        with pytest.raises(ValueError):
            webhook_service.validate_webhook_signature(
                payload=sample_va_webhook_success,
                received_signature=invalid_signature,
            )

    def test_validate_webhook_signature_tampered_payload(
        self,
        webhook_service: WebhookService,
        sample_va_webhook_success: dict,
    ):
        """Test rejection of tampered webhook payload."""
        # Compute signature with original payload
        valid_signature = compute_webhook_signature(
            sample_va_webhook_success,
            webhook_service.secret_key,
        )

        # Tamper with payload
        tampered_payload = sample_va_webhook_success.copy()
        tampered_payload["amount_received"] = "2000.00"  # Changed amount

        with pytest.raises(ValueError):
            webhook_service.validate_webhook_signature(
                payload=tampered_payload,
                received_signature=valid_signature,
            )


class TestPaymentWebhookProcessing:
    """Tests for payment webhook event processing."""

    @pytest.mark.asyncio
    async def test_process_payment_webhook_success(
        self,
        webhook_service: WebhookService,
        sample_payment_webhook: dict,
    ):
        """Test successful payment webhook processing."""
        response = await webhook_service.process_payment_webhook(sample_payment_webhook)

        assert response.success is True
        assert response.reference == "TXN_20250330_001"
        assert "processed successfully" in response.message.lower()

    @pytest.mark.asyncio
    async def test_process_payment_webhook_recurring(
        self,
        webhook_service: WebhookService,
        sample_payment_webhook: dict,
    ):
        """Test processing of recurring payment webhook."""
        sample_payment_webhook["Body"]["is_recurring"] = True
        sample_payment_webhook["Body"]["payment_information"] = {
            "token_id": "AUTH_token123",
            "card_type": "mastercard",
        }

        response = await webhook_service.process_payment_webhook(sample_payment_webhook)

        assert response.success is True

    @pytest.mark.asyncio
    async def test_process_payment_webhook_failed_transaction(
        self,
        webhook_service: WebhookService,
        sample_payment_webhook: dict,
    ):
        """Test processing of failed payment webhook."""
        sample_payment_webhook["Event"] = "charge_failed"
        sample_payment_webhook["Body"]["transaction_status"] = "failed"

        response = await webhook_service.process_payment_webhook(sample_payment_webhook)

        # Should still process successfully even though transaction failed
        assert response.success is True


class TestVAWebhookProcessing:
    """Tests for virtual account webhook event processing."""

    @pytest.mark.asyncio
    async def test_process_va_webhook_success(
        self,
        webhook_service: WebhookService,
        sample_va_webhook_success: dict,
    ):
        """Test processing of successful VA webhook."""
        response = await webhook_service.process_va_webhook(sample_va_webhook_success)

        assert response.success is True
        assert response.reference == "TXN_20250330_001"
        assert "success" in response.message.lower()

    @pytest.mark.asyncio
    async def test_process_va_webhook_expired(
        self,
        webhook_service: WebhookService,
        sample_va_webhook_expired: dict,
    ):
        """Test processing of expired VA webhook."""
        response = await webhook_service.process_va_webhook(sample_va_webhook_expired)

        assert response.success is True
        assert "expired" in response.message.lower()
        # Expired transactions are auto-refunded
        assert "refund" in response.message.lower()

    @pytest.mark.asyncio
    async def test_process_va_webhook_mismatch(
        self,
        webhook_service: WebhookService,
    ):
        """Test processing of mismatched amount VA webhook."""
        payload = {
            "transaction_status": "MISMATCH",
            "merchant_reference": "TXN_MISMATCH",
            "transaction_reference": "REF_MISMATCH",
            "merchant_amount": "1000.00",
            "amount_received": "1500.00",  # Different amount
            "email": "customer@example.com",
            "merchant_id": "TEST_MERCHANT",
            "date": "2025-03-30T10:00:00.000Z",
            "sender_name": "UNKNOWN PAYER",
        }

        response = await webhook_service.process_va_webhook(payload)

        assert response.success is True
        assert "mismatch" in response.message.lower()


class TestWebhookEventLogging:
    """Tests for webhook event logging."""

    @pytest.mark.asyncio
    async def test_webhook_event_logged(
        self,
        webhook_service: WebhookService,
        sample_payment_webhook: dict,
    ):
        """Test that webhook events are logged."""
        with patch("app.services.webhook_service.logger") as mock_logger:
            response = await webhook_service.process_payment_webhook(sample_payment_webhook)

            # Verify logging occurred
            assert mock_logger.info.called
            assert response.success is True

    @pytest.mark.asyncio
    async def test_webhook_error_logging(
        self,
        webhook_service: WebhookService,
    ):
        """Test that webhook processing errors are logged."""
        invalid_payload = {}  # Missing required fields

        with patch("app.services.webhook_service.logger") as mock_logger:
            with pytest.raises((KeyError, AttributeError)):
                await webhook_service.process_payment_webhook(invalid_payload)

            # Verify error logging occurred
            assert mock_logger.error.called
