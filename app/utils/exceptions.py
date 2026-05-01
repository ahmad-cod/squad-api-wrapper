"""
Custom exception classes for Squad API wrapper.

Exceptions are organized by severity and type:
- SquadAPIException: Base exception for all Squad API errors
- SquadAuthenticationError: Authentication/authorization failures
- SquadValidationError: Input validation errors
- SquadRequestError: API request failures
- SquadWebhookError: Webhook processing errors
"""


class SquadAPIException(Exception):
    """Base exception for all Squad API wrapper errors."""

    def __init__(self, message: str, status_code: int | None = None, details: dict | None = None):
        """
        Initialize Squad API Exception.

        Args:
            message: Human-readable error message
            status_code: HTTP status code if applicable
            details: Additional error details (API response, validation errors, etc.)
        """
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        """String representation of exception."""
        parts = [self.message]
        if self.status_code:
            parts.append(f"(HTTP {self.status_code})")
        if self.details:
            parts.append(f"Details: {self.details}")
        return " - ".join(parts)


class SquadAuthenticationError(SquadAPIException):
    """Raised when authentication or authorization fails (401, 403)."""

    pass


class SquadValidationError(SquadAPIException):
    """Raised when input validation fails or API rejects request parameters."""

    pass


class SquadRequestError(SquadAPIException):
    """Raised when Squad API request fails (network, timeout, server error)."""

    pass


class SquadWebhookError(SquadAPIException):
    """Raised when webhook signature validation or processing fails."""

    pass


class SquadNotFoundError(SquadAPIException):
    """Raised when requested resource is not found (404)."""

    pass
