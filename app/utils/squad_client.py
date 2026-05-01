"""
Base Squad API Client - handles HTTP requests, authentication, and error handling.

This module provides a reusable HTTP client for all Squad API operations.
It handles Bearer token authentication, error parsing, retries, and exception raising.
"""

import logging
from typing import Any, Optional

import httpx
from app.utils.exceptions import (
    SquadAPIException,
    SquadAuthenticationError,
    SquadNotFoundError,
    SquadRequestError,
    SquadValidationError,
)

logger = logging.getLogger(__name__)


class SquadAPIClient:
    """Base HTTP client for Squad API operations."""

    def __init__(
        self,
        secret_key: str,
        base_url: str = "https://sandbox-api-d.squadco.com",
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """
        Initialize Squad API Client.

        Args:
            secret_key: Squad API secret key for authentication
            base_url: Base URL for Squad API (sandbox or production)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts for failed requests
        """
        self.secret_key = secret_key
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries

    def _get_headers(self) -> dict[str, str]:
        """
        Get HTTP headers with authentication.

        Returns:
            Dictionary of headers including Bearer token authorization
        """
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

    def _parse_error_response(self, response: httpx.Response) -> dict[str, Any]:
        """
        Parse error response from Squad API.

        Args:
            response: HTTP response object

        Returns:
            Dictionary containing error details
        """
        try:
            data = response.json()
            return {
                "status": data.get("status", response.status_code),
                "message": data.get("message", ""),
                "success": data.get("success", False),
                "details": data.get("data", {}),
            }
        except (ValueError, KeyError):
            return {
                "status": response.status_code,
                "message": response.text or "Unknown error",
                "success": False,
                "details": {},
            }

    def _handle_error_response(self, response: httpx.Response) -> None:
        """
        Parse error response and raise appropriate exception.

        Args:
            response: HTTP response object

        Raises:
            SquadAuthenticationError: For 401/403 responses
            SquadValidationError: For 400/422 responses
            SquadNotFoundError: For 404 responses
            SquadRequestError: For other error responses
        """
        error_data = self._parse_error_response(response)
        message = error_data.get("message", "Unknown error")
        details = error_data.get("details", {})

        if response.status_code in (401, 403):
            raise SquadAuthenticationError(
                message=message or "Authentication failed",
                status_code=response.status_code,
                details=details,
            )
        elif response.status_code in (400, 422):
            raise SquadValidationError(
                message=message or "Validation failed",
                status_code=response.status_code,
                details=details,
            )
        elif response.status_code == 404:
            raise SquadNotFoundError(
                message=message or "Resource not found",
                status_code=response.status_code,
                details=details,
            )
        else:
            raise SquadRequestError(
                message=message or "Request failed",
                status_code=response.status_code,
                details=details,
            )

    async def post(
        self,
        endpoint: str,
        data: Optional[dict[str, Any]] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Make async POST request to Squad API.

        Args:
            endpoint: API endpoint (without base URL)
            data: Request body data
            **kwargs: Additional arguments for httpx.post()

        Returns:
            Parsed JSON response

        Raises:
            SquadAuthenticationError: For auth failures
            SquadValidationError: For validation failures
            SquadRequestError: For network/server errors
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        logger.debug(f"POST {url} with data: {data}")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=data,
                    headers=headers,
                    timeout=self.timeout,
                    **kwargs,
                )

            if response.status_code >= 400:
                self._handle_error_response(response)

            logger.debug(f"POST {url} successful: {response.status_code}")
            return response.json()

        except httpx.RequestError as e:
            logger.error(f"POST {url} failed: {str(e)}")
            raise SquadRequestError(
                message=f"Network request failed: {str(e)}",
                details={"endpoint": endpoint},
            )

    async def get(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Make async GET request to Squad API.

        Args:
            endpoint: API endpoint (without base URL)
            params: Query parameters
            **kwargs: Additional arguments for httpx.get()

        Returns:
            Parsed JSON response

        Raises:
            SquadAuthenticationError: For auth failures
            SquadValidationError: For validation failures
            SquadRequestError: For network/server errors
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        logger.debug(f"GET {url} with params: {params}")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                    **kwargs,
                )

            if response.status_code >= 400:
                self._handle_error_response(response)

            logger.debug(f"GET {url} successful: {response.status_code}")
            return response.json()

        except httpx.RequestError as e:
            logger.error(f"GET {url} failed: {str(e)}")
            raise SquadRequestError(
                message=f"Network request failed: {str(e)}",
                details={"endpoint": endpoint, "params": params},
            )

    async def patch(
        self,
        endpoint: str,
        data: Optional[dict[str, Any]] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Make async PATCH request to Squad API.

        Args:
            endpoint: API endpoint (without base URL)
            data: Request body data
            **kwargs: Additional arguments for httpx.patch()

        Returns:
            Parsed JSON response

        Raises:
            SquadAuthenticationError: For auth failures
            SquadValidationError: For validation failures
            SquadRequestError: For network/server errors
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        logger.debug(f"PATCH {url} with data: {data}")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    url,
                    json=data,
                    headers=headers,
                    timeout=self.timeout,
                    **kwargs,
                )

            if response.status_code >= 400:
                self._handle_error_response(response)

            logger.debug(f"PATCH {url} successful: {response.status_code}")
            return response.json()

        except httpx.RequestError as e:
            logger.error(f"PATCH {url} failed: {str(e)}")
            raise SquadRequestError(
                message=f"Network request failed: {str(e)}",
                details={"endpoint": endpoint},
            )
