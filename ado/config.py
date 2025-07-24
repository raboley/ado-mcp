"""Configuration management for ADO-MCP with structured settings and validation."""

import logging
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

from .errors import AdoConfigurationError

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


@dataclass
class RetryConfig:
    """Configuration for retry policies with exponential backoff."""

    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True

    def __post_init__(self):
        """Validate retry configuration values."""
        if self.max_retries < 0:
            raise AdoConfigurationError(
                "max_retries must be non-negative", context={"max_retries": self.max_retries}
            )

        if self.initial_delay <= 0:
            raise AdoConfigurationError(
                "initial_delay must be positive", context={"initial_delay": self.initial_delay}
            )

        if self.max_delay <= 0:
            raise AdoConfigurationError(
                "max_delay must be positive", context={"max_delay": self.max_delay}
            )

        if self.backoff_multiplier <= 1.0:
            raise AdoConfigurationError(
                "backoff_multiplier must be greater than 1.0",
                context={"backoff_multiplier": self.backoff_multiplier},
            )


@dataclass
class AuthConfig:
    """Configuration for authentication methods and timeouts."""

    timeout_seconds: int = 30
    enable_cli_fallback: bool = True
    enable_interactive_fallback: bool = False
    cache_ttl_seconds: int = 3600

    def __post_init__(self):
        """Validate authentication configuration values."""
        if self.timeout_seconds <= 0:
            raise AdoConfigurationError(
                "timeout_seconds must be positive",
                context={"timeout_seconds": self.timeout_seconds},
            )

        if self.cache_ttl_seconds < 0:
            raise AdoConfigurationError(
                "cache_ttl_seconds must be non-negative",
                context={"cache_ttl_seconds": self.cache_ttl_seconds},
            )


@dataclass
class ConnectionPoolConfig:
    """Configuration for HTTP connection pooling and session management."""

    enabled: bool = True
    max_pool_connections: int = 20
    max_pool_size: int = 100
    block: bool = False
    pool_timeout: float = 5.0

    def __post_init__(self):
        """Validate connection pool configuration values."""
        if self.max_pool_connections <= 0:
            raise AdoConfigurationError(
                "max_pool_connections must be positive",
                context={"max_pool_connections": self.max_pool_connections},
            )

        if self.max_pool_size <= 0:
            raise AdoConfigurationError(
                "max_pool_size must be positive", context={"max_pool_size": self.max_pool_size}
            )

        if self.pool_timeout <= 0:
            raise AdoConfigurationError(
                "pool_timeout must be positive", context={"pool_timeout": self.pool_timeout}
            )


@dataclass
class TelemetryConfig:
    """Configuration for telemetry and observability."""

    enabled: bool = True
    service_name: str = "ado-mcp"
    service_version: str = "1.0.0"
    trace_sampling_rate: float = 1.0
    metrics_enabled: bool = True

    def __post_init__(self):
        """Validate telemetry configuration values."""
        if not 0.0 <= self.trace_sampling_rate <= 1.0:
            raise AdoConfigurationError(
                "trace_sampling_rate must be between 0.0 and 1.0",
                context={"trace_sampling_rate": self.trace_sampling_rate},
            )


@dataclass
class AdoMcpConfig:
    """
    Main configuration class for ADO-MCP with all settings.

    This class consolidates all configuration settings and provides
    environment variable override capabilities.
    """

    # Core settings
    organization_url: str | None = None
    pat: str | None = None

    # Sub-configurations
    retry: RetryConfig = field(default_factory=RetryConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    telemetry: TelemetryConfig = field(default_factory=TelemetryConfig)
    connection_pool: ConnectionPoolConfig = field(default_factory=ConnectionPoolConfig)

    # Request settings
    request_timeout_seconds: int = 30

    def __post_init__(self):
        """Load configuration from environment variables and validate."""
        # Load from environment variables
        self.organization_url = self.organization_url or os.getenv("ADO_ORGANIZATION_URL")
        self.pat = self.pat or os.getenv("AZURE_DEVOPS_EXT_PAT")

        # Override retry config from environment
        self.retry.max_retries = int(os.getenv("ADO_RETRY_MAX_RETRIES", self.retry.max_retries))
        self.retry.initial_delay = float(
            os.getenv("ADO_RETRY_INITIAL_DELAY", self.retry.initial_delay)
        )
        self.retry.max_delay = float(os.getenv("ADO_RETRY_MAX_DELAY", self.retry.max_delay))
        self.retry.backoff_multiplier = float(
            os.getenv("ADO_RETRY_BACKOFF_MULTIPLIER", self.retry.backoff_multiplier)
        )
        self.retry.jitter = os.getenv("ADO_RETRY_JITTER", "true").lower() == "true"

        # Override auth config from environment
        self.auth.timeout_seconds = int(os.getenv("ADO_AUTH_TIMEOUT", self.auth.timeout_seconds))
        self.auth.enable_cli_fallback = os.getenv("ADO_AUTH_CLI_FALLBACK", "true").lower() == "true"
        self.auth.enable_interactive_fallback = (
            os.getenv("ADO_AUTH_INTERACTIVE_FALLBACK", "false").lower() == "true"
        )
        self.auth.cache_ttl_seconds = int(
            os.getenv("ADO_AUTH_CACHE_TTL", self.auth.cache_ttl_seconds)
        )

        # Override telemetry config from environment
        self.telemetry.enabled = os.getenv("ADO_TELEMETRY_ENABLED", "true").lower() == "true"
        self.telemetry.service_name = os.getenv(
            "ADO_TELEMETRY_SERVICE_NAME", self.telemetry.service_name
        )
        self.telemetry.service_version = os.getenv(
            "ADO_TELEMETRY_SERVICE_VERSION", self.telemetry.service_version
        )
        self.telemetry.trace_sampling_rate = float(
            os.getenv("ADO_TELEMETRY_TRACE_SAMPLING_RATE", self.telemetry.trace_sampling_rate)
        )
        self.telemetry.metrics_enabled = (
            os.getenv("ADO_TELEMETRY_METRICS_ENABLED", "true").lower() == "true"
        )

        # Override connection pool config from environment
        self.connection_pool.enabled = (
            os.getenv("ADO_CONNECTION_POOL_ENABLED", "true").lower() == "true"
        )
        self.connection_pool.max_pool_connections = int(
            os.getenv(
                "ADO_CONNECTION_POOL_MAX_CONNECTIONS", self.connection_pool.max_pool_connections
            )
        )
        self.connection_pool.max_pool_size = int(
            os.getenv("ADO_CONNECTION_POOL_MAX_SIZE", self.connection_pool.max_pool_size)
        )
        self.connection_pool.block = (
            os.getenv("ADO_CONNECTION_POOL_BLOCK", "false").lower() == "true"
        )
        self.connection_pool.pool_timeout = float(
            os.getenv("ADO_CONNECTION_POOL_TIMEOUT", self.connection_pool.pool_timeout)
        )

        # Override request timeout from environment
        self.request_timeout_seconds = int(
            os.getenv("ADO_REQUEST_TIMEOUT", self.request_timeout_seconds)
        )

        # Validate configuration
        self._validate()

        logger.info(
            f"Configuration loaded: retry_max={self.retry.max_retries}, "
            f"auth_timeout={self.auth.timeout_seconds}, "
            f"telemetry_enabled={self.telemetry.enabled}, "
            f"connection_pool_enabled={self.connection_pool.enabled}"
        )

    def _validate(self):
        """Validate the complete configuration."""
        if self.request_timeout_seconds <= 0:
            raise AdoConfigurationError(
                "request_timeout_seconds must be positive",
                context={"request_timeout_seconds": self.request_timeout_seconds},
            )

        # Ensure connection pool config is valid
        if (
            self.connection_pool.enabled
            and self.connection_pool.max_pool_size < self.connection_pool.max_pool_connections
        ):
            raise AdoConfigurationError(
                "connection_pool.max_pool_size must be >= max_pool_connections",
                context={
                    "max_pool_size": self.connection_pool.max_pool_size,
                    "max_pool_connections": self.connection_pool.max_pool_connections,
                },
            )

    @classmethod
    def from_env(cls, **overrides) -> "AdoMcpConfig":
        """
        Create configuration from environment variables with optional overrides.

        Args:
            **overrides: Configuration values to override

        Returns:
            AdoMcpConfig: Configured instance
        """
        return cls(**overrides)

    def get_effective_pat(self) -> str | None:
        """
        Get the effective PAT considering all authentication methods.

        Returns:
            Optional[str]: The PAT to use, or None if not available
        """
        return self.pat or os.getenv("AZURE_DEVOPS_EXT_PAT")

    def should_use_cli_fallback(self) -> bool:
        """
        Check if CLI fallback should be used.

        Returns:
            bool: True if CLI fallback is enabled and no PAT is available
        """
        return self.auth.enable_cli_fallback and not self.get_effective_pat()

    def should_use_interactive_fallback(self) -> bool:
        """
        Check if interactive fallback should be used.

        Returns:
            bool: True if interactive fallback is enabled
        """
        return (
            self.auth.enable_interactive_fallback
            and not self.get_effective_pat()
            and self.auth.enable_cli_fallback
        )
