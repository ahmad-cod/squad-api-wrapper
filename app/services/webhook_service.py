"""
Webhook Service - handles webhook event processing and signature validation.

Includes:
- Webhook signature validation
- Payment event processing
- Virtual account event processing
- Event logging and tracking
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional

from app.models.schemas import (
    PaymentWebhookPayload,
    VAWebhookPayload,
    WebhookResponse,
)
from app.utils.webhooks import validate_webhook_signature

logger = logging.getLogger(__name__)


class WebhookService:
    """Service for webhook event processing."""

    def __init__(self, secret_key: str):
        """
        Initialize Webhook Service.

        Args:
            secret_key: Squad secret key for signature validation
        """
        self.secret_key = secret_key

    def validate_webhook_signature(
        self,
        payload: dict[str, Any],
        received_signature: str,
    ) -> bool:
        """
        Validate webhook signature.

        Uses HMAC-SHA512 with specific payload fields to verify webhook authenticity.

        Args:
            payload: Webhook payload dictionary
            received_signature: Signature from x-squad-encrypted-body header

        Returns:
            True if signature is valid, raises exception otherwise

        Raises:
            SquadWebhookError: If signature validation fails

        Example:
            >>> is_valid = service.validate_webhook_signature(payload, signature)
            >>> assert is_valid
        """
        logger.info("Validating webhook signature")

        is_valid = validate_webhook_signature(
            payload=payload,
            received_signature=received_signature,
            secret_key=self.secret_key,
        )

        if not is_valid:
            logger.error("Webhook signature validation failed")
            raise ValueError("Invalid webhook signature")

        logger.info("Webhook signature validated successfully")
        return True

    async def process_payment_webhook(
        self,
        payload: dict[str, Any],
    ) -> WebhookResponse:
        """
        Process a payment webhook event.

        Handles payment completion, failure, and recurring charge events.

        Args:
            payload: Webhook payload from Squad

        Returns:
            WebhookResponse indicating successful processing

        Example:
            >>> payload = {
            ...     "Event": "charge_successful",
            ...     "TransactionRef": "TXN_...",
            ...     "Body": {...}
            ... }
            >>> response = await service.process_payment_webhook(payload)
            >>> print(response.success)
            True
        """
        event_type = payload.get("Event", "unknown")
        transaction_ref = payload.get("TransactionRef", "unknown")
        body = payload.get("Body", {})

        logger.info(f"Processing payment webhook: {event_type} for transaction {transaction_ref}")

        try:
            # Parse payment details
            transaction_status = body.get("transaction_status", "unknown")
            amount = body.get("amount", 0)
            email = body.get("email", "")
            payment_type = body.get("transaction_type", "unknown")

            logger.info(
                f"Payment webhook details - Status: {transaction_status}, Amount: {amount}, "
                f"Email: {email}, Type: {payment_type}"
            )

            # Check for recurring/tokenized card
            is_recurring = body.get("is_recurring", False)
            if is_recurring:
                token_id = body.get("payment_information", {}).get("token_id", "")
                logger.info(f"Recurring payment detected. Token ID: {token_id}")

            # Log webhook event
            await self._log_webhook_event(
                event_type=event_type,
                transaction_ref=transaction_ref,
                status=transaction_status,
                details=body,
                webhook_type="payment",
            )

            return WebhookResponse(
                success=True,
                message=f"Payment webhook processed successfully",
                reference=transaction_ref,
            )

        except Exception as e:
            logger.error(f"Error processing payment webhook: {str(e)}")
            raise

    async def process_va_webhook(
        self,
        payload: dict[str, Any],
    ) -> WebhookResponse:
        """
        Process a virtual account webhook event.

        Handles SUCCESS, EXPIRED, and MISMATCH events for VA transactions.

        Args:
            payload: Webhook payload from Squad

        Returns:
            WebhookResponse indicating successful processing

        Example:
            >>> payload = {
            ...     "transaction_status": "SUCCESS",
            ...     "merchant_reference": "TXN_001",
            ...     "amount_received": "1000.00",
            ...     "merchant_amount": "1000.00",
            ...     ...
            ... }
            >>> response = await service.process_va_webhook(payload)
            >>> print(response.success)
            True
        """
        transaction_status = payload.get("transaction_status", "UNKNOWN")
        merchant_reference = payload.get("merchant_reference", "unknown")
        transaction_reference = payload.get("transaction_reference", "unknown")
        amount_received = payload.get("amount_received", "0")

        logger.info(
            f"Processing VA webhook: {transaction_status} for transaction {merchant_reference} "
            f"({transaction_reference}). Amount: {amount_received} NGN"
        )

        try:
            if transaction_status == "SUCCESS":
                logger.info(f"VA transaction successful: {merchant_reference}")

            elif transaction_status == "EXPIRED":
                logger.info(
                    f"VA transaction expired: {merchant_reference}. "
                    f"Automatic refund will be issued."
                )

            elif transaction_status == "MISMATCH":
                merchant_amount = payload.get("merchant_amount", "0")
                logger.warning(
                    f"VA transaction amount mismatch: {merchant_reference}. "
                    f"Expected: {merchant_amount} NGN, Received: {amount_received} NGN. "
                    f"Automatic refund will be issued."
                )

            # Log webhook event
            await self._log_webhook_event(
                event_type=f"va_{transaction_status.lower()}",
                transaction_ref=merchant_reference,
                status=transaction_status,
                details=payload,
                webhook_type="virtual_account",
            )

            return WebhookResponse(
                success=True,
                message=f"VA webhook ({transaction_status}) processed successfully",
                reference=merchant_reference,
            )

        except Exception as e:
            logger.error(f"Error processing VA webhook: {str(e)}")
            raise

    async def _log_webhook_event(
        self,
        event_type: str,
        transaction_ref: str,
        status: str,
        details: dict[str, Any],
        webhook_type: str,
    ) -> None:
        """
        Log webhook event for audit trail and debugging.

        Args:
            event_type: Type of webhook event
            transaction_ref: Transaction reference
            status: Status of transaction
            details: Full event details
            webhook_type: Type of webhook (payment, virtual_account, etc.)
        """
        webhook_log = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "webhook_type": webhook_type,
            "transaction_ref": transaction_ref,
            "status": status,
            "details_keys": list(details.keys()),
        }

        logger.info(f"Webhook event logged: {json.dumps(webhook_log)}")

        # TODO: Persist webhook log to database if needed
        # await WebhookLog.create(**webhook_log)
