"""
Webhook signature validation utilities.

Handles HMAC-SHA512 signature validation for Squad webhook events.
This ensures webhook authenticity and prevents request forgery.

Reference: Squad docs use SHA-512 HMAC with specific payload format.
"""

import hashlib
import hmac
import json
import logging
from typing import Any

from app.utils.exceptions import SquadWebhookError

logger = logging.getLogger(__name__)


def validate_webhook_signature(
    payload: dict[str, Any],
    received_signature: str,
    secret_key: str,
) -> bool:
    """
    Validate webhook signature using HMAC-SHA512.

    The signature is computed from specific fields in the payload (transaction_reference,
    amount_received, merchant_reference) in alphabetical order.

    Args:
        payload: Webhook payload dictionary
        received_signature: Signature from x-squad-encrypted-body header
        secret_key: Squad secret key for HMAC computation

    Returns:
        True if signature is valid, False otherwise

    Raises:
        SquadWebhookError: If signature validation fails
    """
    try:
        # Extract fields that are part of the signature (alphabetically ordered)
        signature_fields = {
            "amount_received": payload.get("amount_received"),
            "merchant_reference": payload.get("merchant_reference"),
            "transaction_reference": payload.get("transaction_reference"),
        }

        # Create JSON representation with specific format
        # Fields are ordered alphabetically and only include the three required fields
        payload_json = json.dumps(signature_fields, separators=(",", ":"), sort_keys=True)

        logger.debug(f"Validating webhook signature with payload: {payload_json}")

        # Compute HMAC-SHA512
        computed_signature = hmac.new(
            secret_key.encode("utf-8"),
            payload_json.encode("utf-8"),
            hashlib.sha512,
        ).hexdigest()

        # Compare signatures (constant time comparison to prevent timing attacks)
        is_valid = hmac.compare_digest(computed_signature.lower(), received_signature.lower())

        if is_valid:
            logger.info("Webhook signature validation successful")
        else:
            logger.warning(
                f"Webhook signature validation failed. Expected: {computed_signature}, Got: {received_signature}"
            )

        return is_valid

    except Exception as e:
        logger.error(f"Webhook signature validation error: {str(e)}")
        raise SquadWebhookError(
            message="Webhook signature validation failed",
            details={"error": str(e)},
        )


def extract_webhook_signature_from_headers(headers: dict[str, str]) -> str:
    """
    Extract webhook signature from HTTP headers.

    Squad sends the signature in the 'x-squad-encrypted-body' header.

    Args:
        headers: HTTP headers dictionary (case-insensitive)

    Returns:
        Extracted signature string

    Raises:
        SquadWebhookError: If signature header is missing
    """
    # Handle case-insensitive header lookup
    signature_header_names = ["x-squad-encrypted-body", "X-Squad-Encrypted-Body"]

    for header_name in signature_header_names:
        if header_name in headers:
            return headers[header_name]

    raise SquadWebhookError(
        message="Webhook signature header (x-squad-encrypted-body) not found",
        details={"headers": list(headers.keys())},
    )


def compute_webhook_signature(
    payload: dict[str, Any],
    secret_key: str,
) -> str:
    """
    Compute webhook signature for testing/verification purposes.

    Args:
        payload: Webhook payload dictionary
        secret_key: Squad secret key

    Returns:
        Computed HMAC-SHA512 signature as hex string
    """
    signature_fields = {
        "amount_received": payload.get("amount_received"),
        "merchant_reference": payload.get("merchant_reference"),
        "transaction_reference": payload.get("transaction_reference"),
    }

    payload_json = json.dumps(signature_fields, separators=(",", ":"), sort_keys=True)

    signature = hmac.new(
        secret_key.encode("utf-8"),
        payload_json.encode("utf-8"),
        hashlib.sha512,
    ).hexdigest()

    return signature
