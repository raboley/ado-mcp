"""Advanced authentication handling with credential chaining for ADO-MCP."""

import json
import logging
import os
import subprocess
import time
from abc import ABC, abstractmethod
from base64 import b64encode
from dataclasses import dataclass
from pathlib import Path

from .config import AuthConfig
from .errors import AdoAuthenticationError

logger = logging.getLogger(__name__)


@dataclass
class AuthCredential:
    """Represents an authentication credential."""

    token: str
    auth_type: str  # 'basic' or 'bearer'
    method: str  # 'pat', 'azure_cli', 'interactive', etc.
    expires_at: float | None = None
    refresh_token: str | None = None

    def is_expired(self) -> bool:
        """Check if the credential is expired."""
        if self.expires_at is None:
            return False
        return time.time() >= self.expires_at

    def to_header(self) -> dict[str, str]:
        """Convert credential to HTTP Authorization header."""
        if self.auth_type == "basic":
            encoded_token = b64encode(f":{self.token}".encode("ascii")).decode("ascii")
            return {"Authorization": f"Basic {encoded_token}"}
        elif self.auth_type == "bearer":
            return {"Authorization": f"Bearer {self.token}"}
        else:
            raise ValueError(f"Unknown auth type: {self.auth_type}")


class AuthProvider(ABC):
    """Abstract base class for authentication providers."""

    @abstractmethod
    def get_credential(self) -> AuthCredential | None:
        """Get authentication credential."""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get provider name."""
        pass


class PatAuthProvider(AuthProvider):
    """Personal Access Token authentication provider."""

    def __init__(self, pat: str):
        """Initialize with PAT."""
        self.pat = pat

    def get_credential(self) -> AuthCredential | None:
        """Get PAT credential."""
        if not self.pat:
            return None

        return AuthCredential(token=self.pat, auth_type="basic", method="pat")

    def get_name(self) -> str:
        """Get provider name."""
        return "PAT"


class EnvironmentPatAuthProvider(AuthProvider):
    """Environment variable PAT authentication provider."""

    def __init__(self, env_var: str = "AZURE_DEVOPS_EXT_PAT"):
        """Initialize with environment variable name."""
        self.env_var = env_var

    def get_credential(self) -> AuthCredential | None:
        """Get PAT from environment variable."""
        pat = os.environ.get(self.env_var)
        if not pat:
            return None

        return AuthCredential(token=pat, auth_type="basic", method="env_pat")

    def get_name(self) -> str:
        """Get provider name."""
        return f"Environment ({self.env_var})"


class AzureCliFileAuthProvider(AuthProvider):
    """Azure CLI file-based PAT authentication provider."""

    def get_credential(self) -> AuthCredential | None:
        """Get PAT from Azure CLI file storage."""
        try:
            azure_dir = Path.home() / ".azure" / "azuredevops"
            pat_file = azure_dir / "personalAccessTokens"

            if pat_file.exists() and pat_file.stat().st_size > 0:
                # Try to read the PAT file - it's typically a simple text file with the PAT
                try:
                    pat_content = pat_file.read_text().strip()
                    if pat_content and len(pat_content) > 20:  # Basic validation
                        logger.info("Successfully retrieved PAT from Azure DevOps CLI file storage")
                        return AuthCredential(
                            token=pat_content, auth_type="basic", method="azure_cli_file"
                        )
                except Exception as e:
                    logger.debug(f"Could not read PAT file: {e}")

        except Exception as e:
            logger.debug(f"Could not access Azure DevOps CLI PAT file: {e}")

        return None

    def get_name(self) -> str:
        """Get provider name."""
        return "Azure CLI File"


class AzureCliEntraAuthProvider(AuthProvider):
    """Azure CLI Microsoft Entra token authentication provider."""

    def __init__(self, timeout: int = 10):
        """Initialize with timeout."""
        self.timeout = timeout

    def get_credential(self) -> AuthCredential | None:
        """Get Microsoft Entra token for Azure DevOps."""
        try:
            # Use Azure CLI to get Microsoft Entra token for Azure DevOps
            # 499b84ac-1321-427f-aa17-267ca6975798 is Azure DevOps's application ID
            result = subprocess.run(
                [
                    "az",
                    "account",
                    "get-access-token",
                    "--resource",
                    "499b84ac-1321-427f-aa17-267ca6975798",
                ],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            if result.returncode == 0:
                token_data = json.loads(result.stdout)
                access_token = token_data.get("accessToken")
                expires_on = token_data.get("expiresOn")

                if access_token:
                    logger.info(
                        "Successfully obtained Azure CLI Microsoft Entra token for Azure DevOps"
                    )

                    # Parse expiration time
                    expires_at = None
                    if expires_on:
                        try:
                            expires_at = float(expires_on)
                        except (ValueError, TypeError):
                            logger.warning(f"Could not parse token expiration: {expires_on}")

                    return AuthCredential(
                        token=access_token,
                        auth_type="bearer",
                        method="azure_cli_entra",
                        expires_at=expires_at,
                    )
                else:
                    logger.warning("Azure CLI returned empty access token")
            else:
                logger.debug(
                    f"Azure CLI Microsoft Entra authentication not available: {result.stderr}"
                )

        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            json.JSONDecodeError,
            FileNotFoundError,
        ) as e:
            logger.debug(f"Azure CLI Microsoft Entra authentication not available: {e}")

        return None

    def get_name(self) -> str:
        """Get provider name."""
        return "Azure CLI (Entra)"


class InteractiveAuthProvider(AuthProvider):
    """Interactive authentication provider (placeholder for future implementation)."""

    def get_credential(self) -> AuthCredential | None:
        """Get credential through interactive authentication."""
        # This would implement interactive authentication flow
        # For now, this is a placeholder
        logger.info("Interactive authentication not yet implemented")
        return None

    def get_name(self) -> str:
        """Get provider name."""
        return "Interactive"


class AuthManager:
    """
    Manages authentication with credential chaining and caching.

    Implements the credential chaining pattern where multiple authentication
    providers are tried in order until one succeeds.
    """

    def __init__(self, config: AuthConfig):
        """Initialize authentication manager."""
        self.config = config
        self.providers: list[AuthProvider] = []
        self.cached_credential: AuthCredential | None = None
        self.cache_time: float = 0

    def add_provider(self, provider: AuthProvider):
        """Add an authentication provider to the chain."""
        self.providers.append(provider)
        logger.debug(f"Added auth provider: {provider.get_name()}")

    def setup_default_providers(self, explicit_pat: str | None = None):
        """Set up default authentication providers in order of precedence."""
        self.providers.clear()

        # 1. Explicit PAT (highest priority)
        if explicit_pat:
            self.add_provider(PatAuthProvider(explicit_pat))

        # 2. Environment variable PAT
        self.add_provider(EnvironmentPatAuthProvider())

        # 3. Azure CLI file-based PAT
        if self.config.enable_cli_fallback:
            self.add_provider(AzureCliFileAuthProvider())

        # 4. Azure CLI Microsoft Entra token
        if self.config.enable_cli_fallback:
            self.add_provider(AzureCliEntraAuthProvider(self.config.timeout_seconds))

        # 5. Interactive authentication
        if self.config.enable_interactive_fallback:
            self.add_provider(InteractiveAuthProvider())

    def get_credential(self) -> AuthCredential:
        """
        Get authentication credential using credential chaining.

        Returns:
            AuthCredential: Valid authentication credential

        Raises:
            AdoAuthenticationError: If no authentication method succeeds
        """
        # Check cached credential first
        if self._is_cached_credential_valid():
            return self.cached_credential

        # Try each provider in order
        for provider in self.providers:
            try:
                credential = provider.get_credential()
                if credential and not credential.is_expired():
                    logger.info(f"Successfully authenticated using {provider.get_name()}")
                    self._cache_credential(credential)
                    return credential
                elif credential and credential.is_expired():
                    logger.debug(f"Credential from {provider.get_name()} is expired")
                else:
                    logger.debug(f"No credential available from {provider.get_name()}")
            except Exception as e:
                logger.warning(f"Authentication provider {provider.get_name()} failed: {e}")

        # No provider succeeded
        provider_names = [p.get_name() for p in self.providers]
        raise AdoAuthenticationError(
            f"No authentication method succeeded. Tried: {', '.join(provider_names)}",
            context={
                "providers_tried": provider_names,
                "cli_fallback_enabled": self.config.enable_cli_fallback,
                "interactive_fallback_enabled": self.config.enable_interactive_fallback,
            },
        )

    def _is_cached_credential_valid(self) -> bool:
        """Check if cached credential is still valid."""
        if not self.cached_credential:
            return False

        # Check if cache is expired
        if time.time() - self.cache_time > self.config.cache_ttl_seconds:
            return False

        # Check if credential is expired
        if self.cached_credential.is_expired():
            return False

        return True

    def _cache_credential(self, credential: AuthCredential):
        """Cache the credential."""
        self.cached_credential = credential
        self.cache_time = time.time()

    def invalidate_cache(self):
        """Invalidate the cached credential."""
        self.cached_credential = None
        self.cache_time = 0
        logger.debug("Authentication cache invalidated")

    def get_auth_headers(self) -> dict[str, str]:
        """
        Get authentication headers for HTTP requests.

        Returns:
            Dict[str, str]: Headers dictionary with authentication
        """
        credential = self.get_credential()
        headers = credential.to_header()
        headers["Content-Type"] = "application/json"
        return headers

    def get_auth_method(self) -> str:
        """
        Get the current authentication method.

        Returns:
            str: Authentication method name
        """
        if self.cached_credential:
            return self.cached_credential.method

        # Try to get credential and return its method
        try:
            credential = self.get_credential()
            return credential.method
        except AdoAuthenticationError:
            return "none"
