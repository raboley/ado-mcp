"""Azure DevOps client with core functionality and pipeline operations."""

import json
import logging
import os
import subprocess
from base64 import b64encode
from typing import Any

import requests
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from .errors import AdoAuthenticationError
from .models import Project
from .pipelines import BuildOperations, LogOperations, PipelineOperations
from .lookups import AdoLookups

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

    def __init__(self, organization_url: str, pat: str = None):
        """Initialize the Azure DevOps client."""
        self.organization_url = organization_url
        self.auth_method = "unknown"

        # Try authentication methods in order of precedence
        if pat:
            self._setup_pat_auth(pat)
            self.auth_method = "explicit_pat"
        elif os.environ.get("AZURE_DEVOPS_EXT_PAT"):
            self._setup_pat_auth(os.environ.get("AZURE_DEVOPS_EXT_PAT"))
            self.auth_method = "env_pat"
        else:
            # Try Azure CLI authentication
            azure_token = self._get_azure_cli_token()
            if azure_token:
                # Check if this looks like a PAT or a Bearer token
                if len(azure_token) < 100 and azure_token.isalnum():
                    # Likely a PAT - use Basic auth
                    self._setup_pat_auth(azure_token)
                else:
                    # Likely a Bearer token - use Bearer auth
                    self._setup_bearer_auth(azure_token)
                self.auth_method = "azure_cli"
            else:
                raise ValueError(
                    "No authentication method available. Either:\n"
                    "1. Provide a PAT parameter\n"
                    "2. Set AZURE_DEVOPS_EXT_PAT environment variable\n"
                    "3. Login with 'az login' or 'az devops login' for Azure CLI authentication"
                )

        logger.info(f"AdoClient initialized using {self.auth_method} authentication.")

        # Initialize operation modules
        self._pipelines = PipelineOperations(self)
        self._builds = BuildOperations(self)
        self._logs = LogOperations(self)
        self._lookups = AdoLookups(self)

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
                    logger.info("Successfully obtained Azure CLI Microsoft Entra token for Azure DevOps")
                    return access_token
                else:
                    logger.warning("Azure CLI returned empty access token")
            else:
                logger.debug(f"Azure CLI Microsoft Entra authentication not available: {result.stderr}")

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
                logger.info("User is logged into Azure DevOps CLI, but PAT is stored in system keyring")
                logger.info("Try 'az devops logout' then 'az devops login' to store PAT in file instead")
            
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
                "which likely means the Personal Access Token (PAT) is invalid or expired."
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
                        "which likely means the Personal Access Token (PAT) is invalid or expired."
                    )
            except (ValueError, KeyError):
                # If we can't parse JSON or find expected fields, continue normal processing
                pass

    def _send_request(self, method: str, url: str, **kwargs) -> dict[str, Any]:
        """
        Send an authenticated request to the Azure DevOps API.

        This method handles common request logic, including adding authentication
        headers, validating the response, and raising appropriate exceptions
        for HTTP or network errors.

        Args:
            method (str): The HTTP method (e.g., 'GET', 'POST').
            url (str): The full URL for the API endpoint.
            **kwargs: Additional keyword arguments to pass to `requests.request`.

        Returns:
            dict or None: The parsed JSON response from the API, or None if the
            response has no content.

        Raises:
            requests.exceptions.HTTPError: For HTTP-related errors (e.g., 404, 500).
            requests.exceptions.RequestException: For other network-related errors.
        """
        try:
            response = requests.request(method, url, headers=self.headers, **kwargs)
            self._validate_response(response)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            logger.error(f"HTTP Error: {http_err} - Response Body: {http_err.response.text}")
            raise

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
        try:
            url = f"{self.organization_url}/_apis/connectionData?api-version=7.1-preview.1"
            logger.debug("Testing authentication with ConnectionData endpoint")
            self._send_request("GET", url)
            logger.info("✅ Authentication successful")
            return True
        except AdoAuthenticationError:
            logger.error("❌ Authentication failed - invalid or expired PAT")
            raise
        except Exception as e:
            logger.error(f"Authentication check failed with an exception: {e}")
            raise AdoAuthenticationError(f"Authentication check failed: {e}") from e

    def list_projects(self) -> list[Project]:
        """
        Retrieve a list of projects in the organization.

        Returns:
            List[Project]: A list of Project objects.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
        """
        with tracer.start_as_current_span("ado_list_projects") as span:
            span.set_attribute("ado.operation", "list_projects")
            span.set_attribute("ado.organization_url", self.organization_url)
            
            url = f"{self.organization_url}/_apis/projects?api-version=7.1-preview.4"
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
    def run_pipeline(self, project_id: str, pipeline_id: int):
        """Run a pipeline."""
        return self._builds.run_pipeline(project_id, pipeline_id)

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
        self, project_id: str, pipeline_id: int, timeout_seconds: int = 300, max_lines: int = 100
    ):
        """Run pipeline and get complete outcome."""
        return self._builds.run_pipeline_and_get_outcome(
            project_id, pipeline_id, timeout_seconds, max_lines
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

    def run_pipeline_by_name(self, project_name: str, pipeline_name: str):
        """Run pipeline by project and pipeline names."""
        return self._lookups.run_pipeline_by_name(project_name, pipeline_name)

    def get_pipeline_failure_summary_by_name(
        self, project_name: str, pipeline_name: str, run_id: int, max_lines: int = 100
    ):
        """Get pipeline failure summary by names."""
        return self._lookups.get_pipeline_failure_summary_by_name(
            project_name, pipeline_name, run_id, max_lines
        )

    def run_pipeline_and_get_outcome_by_name(
        self, project_name: str, pipeline_name: str, timeout_seconds: int = 300, max_lines: int = 100
    ):
        """Run pipeline by name and get outcome."""
        return self._lookups.run_pipeline_and_get_outcome_by_name(
            project_name, pipeline_name, timeout_seconds, max_lines
        )

    def list_available_projects(self):
        """Get list of available project names."""
        return self._lookups.list_available_projects()

    def list_available_pipelines(self, project_name: str):
        """Get list of available pipeline names for a project."""
        return self._lookups.list_available_pipelines(project_name)
