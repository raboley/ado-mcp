"""Azure DevOps client with core functionality and pipeline operations."""

import json
import logging
import os
import subprocess
import uuid
from base64 import b64encode
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from .config import AdoMcpConfig
from .errors import AdoAuthenticationError, AdoRateLimitError, AdoNetworkError, AdoTimeoutError
from .models import Project
from .pipelines import BuildOperations, LogOperations, PipelineOperations
from .lookups import AdoLookups
from .retry import RetryManager
from .telemetry import get_telemetry_manager, initialize_telemetry
from .auth import AuthManager

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class AdoClient:
    """
    A client for interacting with the Azure DevOps REST API.

    Handles authentication and provides methods for making API requests.
    Pipeline operations are organized into separate modules for better maintainability.

    Authentication Methods (in order of precedence):
    1. Explicit PAT parameter
    2. AZURE_DEVOPS_EXT_PAT environment variable
    3. Azure CLI authentication (Microsoft Entra token via 'az account get-access-token --resource 499b84ac-1321-427f-aa17-267ca6975798')

    Note: The Azure CLI method now correctly uses Microsoft Entra tokens for Azure DevOps
    instead of trying to access stored PATs from 'az devops login'.

    Args:
        organization_url (str): The URL of the Azure DevOps organization.
        pat (str, optional): A Personal Access Token for authentication.
            If not provided, will try environment variable and Azure CLI.

    Raises:
        ValueError: If no authentication method is available.
    """

    def __init__(self, organization_url: str = None, pat: str = None, config: AdoMcpConfig = None):
        """Initialize the Azure DevOps client."""
        # Initialize configuration
        self.config = config or AdoMcpConfig()
        self.organization_url = organization_url or self.config.organization_url

        if not self.organization_url:
            raise ValueError(
                "Organization URL is required. Either provide it as a parameter or set ADO_ORGANIZATION_URL environment variable."
            )

        # Initialize telemetry if enabled
        self.telemetry = get_telemetry_manager()
        if not self.telemetry and self.config.telemetry.enabled:
            self.telemetry = initialize_telemetry(self.config.telemetry)

        # Initialize retry manager
        self.retry_manager = RetryManager(self.config.retry)

        # Initialize connection pooling session if enabled
        self.session = self._create_session() if self.config.connection_pool.enabled else requests

        # Generate correlation ID for this client instance
        self.correlation_id = str(uuid.uuid4())

        # Initialize authentication manager
        self.auth_manager = AuthManager(self.config.auth)
        self.auth_manager.setup_default_providers(pat)

        # Get authentication headers
        try:
            self.headers = self.auth_manager.get_auth_headers()
            self.auth_method = self._get_compatible_auth_method()
        except AdoAuthenticationError as e:
            if self.telemetry:
                self.telemetry.record_auth_attempt("none", False)
            # Convert to ValueError for backward compatibility
            raise ValueError(str(e)) from e

        logger.info(
            f"AdoClient initialized using {self.auth_method} authentication with correlation_id={self.correlation_id}"
        )

        # Record authentication attempt
        if self.telemetry:
            self.telemetry.record_auth_attempt(self.auth_method, True)
            self.telemetry.add_correlation_id(self.correlation_id)

        # Initialize operation modules
        self._pipelines = PipelineOperations(self)
        self._builds = BuildOperations(self)
        self._logs = LogOperations(self)
        self._lookups = AdoLookups(self)

        logger.info(
            f"AdoClient initialized with connection_pool_enabled={self.config.connection_pool.enabled}"
        )

    def _get_compatible_auth_method(self) -> str:
        """Get authentication method name compatible with existing tests."""
        actual_method = self.auth_manager.get_auth_method()

        # Map new method names to old ones for compatibility
        method_mapping = {
            "pat": "explicit_pat",
            "env_pat": "env_pat",
            "azure_cli_file": "azure_cli",
            "azure_cli_entra": "azure_cli",
            "interactive": "interactive",
        }

        return method_mapping.get(actual_method, actual_method)

    def _create_session(self) -> requests.Session:
        """
        Create a requests session with connection pooling and retry configuration.

        Returns:
            requests.Session: Configured session with pooling
        """
        session = requests.Session()

        # Configure HTTP adapter with connection pooling
        adapter = HTTPAdapter(
            pool_connections=self.config.connection_pool.max_pool_connections,
            pool_maxsize=self.config.connection_pool.max_pool_size,
            pool_block=self.config.connection_pool.block,
        )

        # Mount adapters for HTTP and HTTPS
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        logger.info(
            f"Connection pool configured: max_connections={self.config.connection_pool.max_pool_connections}, "
            f"max_size={self.config.connection_pool.max_pool_size}, "
            f"block={self.config.connection_pool.block}"
        )

        return session

    def close(self):
        """
        Close the connection pool session if it exists.

        This method should be called when the client is no longer needed
        to properly clean up connection pool resources.
        """
        if hasattr(self, "session") and self.session != requests and hasattr(self.session, "close"):
            logger.info("Closing connection pool session")
            self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.close()

    def _setup_pat_auth(self, pat: str) -> None:
        """Set up PAT-based authentication headers."""
        encoded_pat = b64encode(f":{pat}".encode("ascii")).decode("ascii")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {encoded_pat}",
        }

    def _setup_bearer_auth(self, token: str) -> None:
        """Set up Bearer token authentication headers."""
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

    def _get_azure_cli_token(self) -> str | None:
        """
        Get an access token from Azure CLI for Azure DevOps.

        Tries multiple methods in order:
        1. Read stored PAT from Azure DevOps CLI file storage (if available)
        2. Try Microsoft Entra token via Azure CLI (may not work for all organizations)
        3. Check if user is logged into Azure DevOps CLI and provide guidance

        Returns:
            str | None: Access token/PAT if Azure CLI authentication is available, None otherwise.
        """
        # Method 1: Try to read stored PAT from Azure DevOps CLI file storage
        try:
            import pathlib

            azure_dir = pathlib.Path.home() / ".azure" / "azuredevops"
            pat_file = azure_dir / "personalAccessTokens"

            if pat_file.exists() and pat_file.stat().st_size > 0:
                # Try to read the PAT file - it's typically a simple text file with the PAT
                try:
                    pat_content = pat_file.read_text().strip()
                    if pat_content and len(pat_content) > 20:  # Basic validation
                        logger.info("Successfully retrieved PAT from Azure DevOps CLI file storage")
                        return pat_content
                except Exception as e:
                    logger.debug(f"Could not read PAT file: {e}")

        except Exception as e:
            logger.debug(f"Could not access Azure DevOps CLI PAT file: {e}")

        # Method 2: Try to get Microsoft Entra token for Azure DevOps (may not work for all orgs)
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
                timeout=10,
            )

            if result.returncode == 0:
                token_data = json.loads(result.stdout)
                access_token = token_data.get("accessToken")
                if access_token:
                    logger.info(
                        "Successfully obtained Azure CLI Microsoft Entra token for Azure DevOps"
                    )
                    return access_token
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

        # Method 3: Check if Azure DevOps CLI has stored credentials and provide guidance
        try:
            # Test if user is logged into Azure DevOps CLI by checking organization info
            result = subprocess.run(
                ["az", "devops", "configure", "--list"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0 and "organization" in result.stdout:
                # User is logged in via az devops login, but stored in keyring (not accessible)
                logger.info(
                    "User is logged into Azure DevOps CLI, but PAT is stored in system keyring"
                )
                logger.info(
                    "Try 'az devops logout' then 'az devops login' to store PAT in file instead"
                )

        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
        ) as e:
            logger.debug(f"Azure DevOps CLI check failed: {e}")

        logger.info("No Azure CLI authentication available. Try one of these options:")
        logger.info("1. Set AZURE_DEVOPS_EXT_PAT environment variable")
        logger.info("2. Run 'az devops login' with your PAT")
        logger.info("3. Install 'keyrings.alt' package to enable keyring storage")

        return None

    def refresh_authentication(self):
        """Refresh authentication credentials."""
        try:
            self.auth_manager.invalidate_cache()
            self.headers = self.auth_manager.get_auth_headers()
            self.auth_method = self._get_compatible_auth_method()

            if self.telemetry:
                self.telemetry.record_auth_attempt(self.auth_method, True)

            logger.info(f"Authentication refreshed using {self.auth_method}")

        except AdoAuthenticationError as e:
            if self.telemetry:
                self.telemetry.record_auth_attempt("none", False)
            raise e

    def _validate_response(self, response: requests.Response) -> None:
        """
        Check if the response indicates an authentication failure.

        Azure DevOps returns different patterns for authentication failures:
        1. HTML sign-in page for some endpoints
        2. Anonymous user response for connectionData endpoint

        Args:
            response (requests.Response): The HTTP response object.

        Raises:
            AdoAuthenticationError: If the response indicates authentication failure.
        """
        # Check for HTML sign-in page
        if "Sign In" in response.text:
            logger.error(
                "Authentication failed: Response contains sign-in page. "
                f"Response text: {response.text[:200]}..."
            )
            raise AdoAuthenticationError(
                "Authentication failed. The response contained a sign-in page, "
                "which likely means the Personal Access Token (PAT) is invalid or expired.",
                context={
                    "correlation_id": self.correlation_id,
                    "url": str(response.url),
                    "status_code": response.status_code,
                    "auth_method": self.auth_method,
                },
            )

        # Check for anonymous user in connectionData response (specific to auth check)
        if response.url and "connectionData" in response.url:
            try:
                data = response.json()
                authenticated_user = data.get("authenticatedUser", {})
                if authenticated_user.get("providerDisplayName") == "Anonymous":
                    logger.error(
                        "Authentication failed: Received Anonymous user response. "
                        f"User ID: {authenticated_user.get('id')}"
                    )
                    raise AdoAuthenticationError(
                        "Authentication failed. The response contained a sign-in page, "
                        "which likely means the Personal Access Token (PAT) is invalid or expired.",
                        context={
                            "correlation_id": self.correlation_id,
                            "url": str(response.url),
                            "user_id": authenticated_user.get("id"),
                            "auth_method": self.auth_method,
                        },
                    )
            except (ValueError, KeyError):
                # If we can't parse JSON or find expected fields, continue normal processing
                pass

    def _send_request(self, method: str, url: str, **kwargs) -> dict[str, Any]:
        """
        Send an authenticated request to the Azure DevOps API with retry logic.

        This method handles common request logic, including adding authentication
        headers, validating the response, retry logic, and raising appropriate
        exceptions for HTTP or network errors.

        Args:
            method (str): The HTTP method (e.g., 'GET', 'POST').
            url (str): The full URL for the API endpoint.
            **kwargs: Additional keyword arguments to pass to `requests.request`.

        Returns:
            dict or None: The parsed JSON response from the API, or None if the
            response has no content.

        Raises:
            AdoRateLimitError: For rate limiting (429) errors.
            AdoNetworkError: For network-related errors.
            AdoTimeoutError: For timeout errors.
            requests.exceptions.HTTPError: For other HTTP-related errors.
        """
        # Set up request with timeout
        kwargs.setdefault("timeout", self.config.request_timeout_seconds)

        @self.retry_manager.retry_on_failure
        def make_request():
            try:
                # Use session for connection pooling if enabled, otherwise fall back to requests
                request_func = (
                    self.session.request
                    if hasattr(self, "session") and self.session != requests
                    else requests.request
                )
                response = request_func(method, url, headers=self.headers, **kwargs)
                self._validate_response(response)

                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        try:
                            retry_after = int(retry_after)
                        except ValueError:
                            retry_after = None

                    raise AdoRateLimitError(
                        f"Rate limit exceeded for {method} {url}",
                        retry_after=retry_after,
                        context={
                            "correlation_id": self.correlation_id,
                            "method": method,
                            "url": url,
                            "status_code": response.status_code,
                        },
                    )

                response.raise_for_status()
                return response.json() if response.content else None

            except requests.exceptions.HTTPError as e:
                # Log HTTP errors for backward compatibility
                logger.error(
                    f"HTTP Error: {e} - Response Body: {e.response.text if e.response and e.response.text else 'No response'}"
                )
                # For backward compatibility, let all HTTP errors through as HTTPError
                # The retry logic will handle whether to retry or not
                raise e
            except requests.exceptions.Timeout as e:
                raise AdoTimeoutError(
                    f"Request timeout for {method} {url}",
                    timeout_seconds=self.config.request_timeout_seconds,
                    context={
                        "correlation_id": self.correlation_id,
                        "method": method,
                        "url": url,
                    },
                    original_exception=e,
                )
            except requests.exceptions.RequestException as e:
                if hasattr(e, "response") and e.response is not None:
                    # Log response details for debugging
                    logger.error(
                        f"HTTP Error: {e} - Status: {e.response.status_code} - "
                        f"Response Body: {e.response.text[:500]}..."
                    )

                    # Let rate limit errors be handled above
                    if e.response.status_code == 429:
                        raise

                raise AdoNetworkError(
                    f"Network error for {method} {url}: {str(e)}",
                    context={
                        "correlation_id": self.correlation_id,
                        "method": method,
                        "url": url,
                        "error_type": type(e).__name__,
                    },
                    original_exception=e,
                )

        return make_request()

    def check_authentication(self) -> bool:
        """
        Verify that the provided credentials are valid.

        Makes a simple API call to the ConnectionData endpoint to verify
        that the Personal Access Token is working correctly.

        Returns:
            bool: True if authentication is successful, False otherwise.

        Raises:
            AdoAuthenticationError: If authentication fails due to invalid credentials.
            requests.exceptions.RequestException: For other network-related errors.
        """
        operation_name = "check_authentication"

        try:
            url = f"{self.organization_url}/_apis/connectionData?api-version=7.1-preview.1"
            logger.debug("Testing authentication with ConnectionData endpoint")

            # Use telemetry context if available
            if self.telemetry:
                with self.telemetry.trace_api_call(
                    operation_name,
                    **{
                        "ado.url": url,
                        "ado.auth_method": self.auth_method,
                        "correlation_id": self.correlation_id,
                    },
                ):
                    self._send_request("GET", url)
            else:
                self._send_request("GET", url)

            logger.info("✅ Authentication successful")

            if self.telemetry:
                self.telemetry.record_auth_attempt(self.auth_method, True)

            return True

        except AdoAuthenticationError:
            logger.error("❌ Authentication failed - invalid or expired PAT")
            if self.telemetry:
                self.telemetry.record_auth_attempt(self.auth_method, False)
            raise
        except Exception as e:
            logger.error(f"Authentication check failed with an exception: {e}")
            if self.telemetry:
                self.telemetry.record_auth_attempt(self.auth_method, False)
            raise AdoAuthenticationError(
                f"Authentication check failed: {e}",
                context={
                    "correlation_id": self.correlation_id,
                    "auth_method": self.auth_method,
                    "error_type": type(e).__name__,
                },
                original_exception=e,
            ) from e

    def list_projects(self) -> list[Project]:
        """
        Retrieve a list of projects in the organization.

        Returns:
            List[Project]: A list of Project objects.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
        """
        operation_name = "list_projects"
        url = f"{self.organization_url}/_apis/projects?api-version=7.1-preview.4"

        context_attrs = {
            "ado.organization_url": self.organization_url,
            "ado.url": url,
            "correlation_id": self.correlation_id,
        }

        if self.telemetry:
            with self.telemetry.trace_api_call(operation_name, **context_attrs) as span:
                return self._list_projects_impl(url, span)
        else:
            with tracer.start_as_current_span(f"ado_{operation_name}") as span:
                span.set_attribute("ado.operation", operation_name)
                for key, value in context_attrs.items():
                    span.set_attribute(key, value)
                return self._list_projects_impl(url, span)

    def _list_projects_impl(self, url: str, span) -> list[Project]:
        """Implementation of list_projects with span context."""
        logger.info("Fetching list of projects")
        response = self._send_request("GET", url)
        projects_data = response.get("value", [])

        span.set_attribute("ado.projects_count", len(projects_data))
        logger.info(f"Retrieved {len(projects_data)} projects")

        if projects_data:
            logger.debug(f"First project data: {projects_data[0]}")

        projects = []
        for project_data in projects_data:
            try:
                project = Project(**project_data)
                projects.append(project)
                logger.debug(f"Parsed project: {project.name} (ID: {project.id})")
            except Exception as e:
                logger.error(f"Failed to parse project data: {project_data}. Error: {e}")
                span.record_exception(e)

        return projects

    def list_service_connections(self, project_id: str) -> list[dict[str, Any]]:
        """
        List service connections for a given project.

        Args:
            project_id (str): The ID of the project.

        Returns:
            List[dict]: A list of service connection objects.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
        """
        url = f"{self.organization_url}/{project_id}/_apis/serviceendpoint/endpoints?api-version=7.2-preview.4"
        logger.info(f"Fetching service connections for project {project_id}")
        response = self._send_request("GET", url)
        connections_data = response.get("value", [])
        logger.info(
            f"Retrieved {len(connections_data)} service connections for project {project_id}"
        )

        if connections_data:
            logger.debug(f"First service connection: {connections_data[0]}")

        return connections_data

    # Pipeline Operations - delegated to specialized modules
    def list_pipelines(self, project_id: str):
        """List pipelines for a project."""
        return self._pipelines.list_pipelines(project_id)

    def create_pipeline(self, project_id: str, request):
        """Create a new pipeline."""
        return self._pipelines.create_pipeline(project_id, request)

    def delete_pipeline(self, project_id: str, pipeline_id: int):
        """Delete a pipeline."""
        return self._pipelines.delete_pipeline(project_id, pipeline_id)

    def get_pipeline(self, project_id: str, pipeline_id: int):
        """Get pipeline details."""
        return self._pipelines.get_pipeline(project_id, pipeline_id)

    def preview_pipeline(self, project_id: str, pipeline_id: int, request=None):
        """Preview a pipeline."""
        return self._pipelines.preview_pipeline(project_id, pipeline_id, request)

    # Build Operations
    def run_pipeline(self, project_id: str, pipeline_id: int, request=None):
        """Run a pipeline."""
        return self._builds.run_pipeline(project_id, pipeline_id, request)

    def get_pipeline_run(self, project_id: str, pipeline_id: int, run_id: int):
        """Get pipeline run details."""
        return self._builds.get_pipeline_run(project_id, pipeline_id, run_id)

    def get_build_by_id(self, project_id: str, build_id: int):
        """Get build details by ID."""
        return self._builds.get_build_by_id(project_id, build_id)

    def wait_for_pipeline_completion(
        self,
        project_id: str,
        pipeline_id: int,
        run_id: int,
        timeout_seconds: int = 300,
        poll_interval_seconds: int = 10,
    ):
        """Wait for pipeline completion."""
        return self._builds.wait_for_pipeline_completion(
            project_id, pipeline_id, run_id, timeout_seconds, poll_interval_seconds
        )

    def run_pipeline_and_get_outcome(
        self,
        project_id: str,
        pipeline_id: int,
        request=None,
        timeout_seconds: int = 300,
        max_lines: int = 100,
    ):
        """Run pipeline and get complete outcome."""
        return self._builds.run_pipeline_and_get_outcome(
            project_id, pipeline_id, request, timeout_seconds, max_lines
        )

    # Log Operations
    def list_pipeline_logs(self, project_id: str, pipeline_id: int, run_id: int):
        """List pipeline logs."""
        return self._logs.list_pipeline_logs(project_id, pipeline_id, run_id)

    def get_log_content_by_id(
        self, project_id: str, pipeline_id: int, run_id: int, log_id: int, max_lines: int = 100
    ):
        """Get log content by ID."""
        return self._logs.get_log_content_by_id(project_id, pipeline_id, run_id, log_id, max_lines)

    def get_pipeline_timeline(self, project_id: str, pipeline_id: int, run_id: int):
        """Get pipeline timeline."""
        return self._logs.get_pipeline_timeline(project_id, pipeline_id, run_id)

    def get_pipeline_failure_summary(
        self, project_id: str, pipeline_id: int, run_id: int, max_lines: int = 100
    ):
        """Get pipeline failure summary."""
        return self._logs.get_pipeline_failure_summary(project_id, pipeline_id, run_id, max_lines)

    def get_failed_step_logs(
        self, project_id: str, pipeline_id: int, run_id: int, step_name=None, max_lines: int = 100
    ):
        """Get failed step logs."""
        return self._logs.get_failed_step_logs(
            project_id, pipeline_id, run_id, step_name, max_lines
        )

    # Name-based lookup operations
    def find_project_by_name(self, name: str):
        """Find project by name with fuzzy matching."""
        return self._lookups.find_project(name)

    def find_pipeline_by_name(self, project_name: str, pipeline_name: str):
        """Find pipeline by project and pipeline names."""
        return self._lookups.find_pipeline(project_name, pipeline_name)

    def run_pipeline_by_name(self, project_name: str, pipeline_name: str, request=None):
        """Run pipeline by project and pipeline names."""
        return self._lookups.run_pipeline_by_name(project_name, pipeline_name, request)

    def get_pipeline_failure_summary_by_name(
        self, project_name: str, pipeline_name: str, run_id: int, max_lines: int = 100
    ):
        """Get pipeline failure summary by names."""
        return self._lookups.get_pipeline_failure_summary_by_name(
            project_name, pipeline_name, run_id, max_lines
        )

    def run_pipeline_and_get_outcome_by_name(
        self,
        project_name: str,
        pipeline_name: str,
        request=None,
        timeout_seconds: int = 300,
        max_lines: int = 100,
    ):
        """Run pipeline by name and get outcome."""
        return self._lookups.run_pipeline_and_get_outcome_by_name(
            project_name, pipeline_name, request, timeout_seconds, max_lines
        )

    def list_available_projects(self):
        """Get list of available project names."""
        return self._lookups.list_available_projects()

    def list_available_pipelines(self, project_name: str):
        """Get list of available pipeline names for a project."""
        return self._lookups.list_available_pipelines(project_name)
