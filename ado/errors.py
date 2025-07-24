from typing import Any


class AdoError(Exception):
    """Base exception class for ADO-related errors with structured error information."""

    def __init__(
        self,
        message: str,
        error_code: str,
        context: dict[str, Any] | None = None,
        original_exception: Exception | None = None,
    ):
        """
        Initialize structured ADO error.

        Args:
            message: Human-readable error message
            error_code: Structured error code for programmatic handling
            context: Additional context information about the error
            original_exception: The original exception that caused this error
        """
        super().__init__(message)
        self.error_code = error_code
        self.context = context or {}
        self.original_exception = original_exception


class AdoAuthenticationError(AdoError):
    """Custom exception for ADO authentication failures."""

    def __init__(
        self,
        message: str = "Authentication failed",
        context: dict[str, Any] | None = None,
        original_exception: Exception | None = None,
    ):
        super().__init__(
            message=message,
            error_code="ADO_AUTH_FAILED",
            context=context,
            original_exception=original_exception,
        )


class AdoRateLimitError(AdoError):
    """Exception for ADO API rate limiting (429 errors)."""

    def __init__(
        self,
        message: str = "API rate limit exceeded",
        retry_after: int | None = None,
        context: dict[str, Any] | None = None,
        original_exception: Exception | None = None,
    ):
        context = context or {}
        if retry_after:
            context["retry_after"] = retry_after

        super().__init__(
            message=message,
            error_code="ADO_RATE_LIMIT",
            context=context,
            original_exception=original_exception,
        )
        self.retry_after = retry_after


class AdoTimeoutError(AdoError):
    """Exception for ADO operation timeouts."""

    def __init__(
        self,
        message: str = "Operation timed out",
        timeout_seconds: int | None = None,
        context: dict[str, Any] | None = None,
        original_exception: Exception | None = None,
    ):
        context = context or {}
        if timeout_seconds:
            context["timeout_seconds"] = timeout_seconds

        super().__init__(
            message=message,
            error_code="ADO_TIMEOUT",
            context=context,
            original_exception=original_exception,
        )
        self.timeout_seconds = timeout_seconds


class AdoNetworkError(AdoError):
    """Exception for network-related failures."""

    def __init__(
        self,
        message: str = "Network error occurred",
        context: dict[str, Any] | None = None,
        original_exception: Exception | None = None,
    ):
        super().__init__(
            message=message,
            error_code="ADO_NETWORK_ERROR",
            context=context,
            original_exception=original_exception,
        )


class AdoConfigurationError(AdoError):
    """Exception for configuration-related errors."""

    def __init__(
        self,
        message: str = "Configuration error",
        context: dict[str, Any] | None = None,
        original_exception: Exception | None = None,
    ):
        super().__init__(
            message=message,
            error_code="ADO_CONFIG_ERROR",
            context=context,
            original_exception=original_exception,
        )
