import os
import requests
from base64 import b64encode
import logging
from .errors import AdoAuthenticationError

logger = logging.getLogger(__name__)


class AdoClient:
    """
    A client for interacting with the Azure DevOps REST API.

    Handles authentication and provides methods for making API requests.

    Args:
        organization_url (str): The URL of the Azure DevOps organization.
        pat (str, optional): A Personal Access Token for authentication.
            If not provided, it will be read from the `AZURE_DEVOPS_EXT_PAT`
            environment variable.

    Raises:
        ValueError: If the Personal Access Token is not provided or found
            in the environment variables.
    """

    def __init__(self, organization_url: str, pat: str = None):
        self.organization_url = organization_url
        if not pat:
            pat = os.environ.get("AZURE_DEVOPS_EXT_PAT")
        if not pat:
            raise ValueError("Personal Access Token (PAT) not provided or found in environment variables.")

        encoded_pat = b64encode(f":{pat}".encode("ascii")).decode("ascii")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {encoded_pat}"
        }
        logger.info("AdoClient initialized.")

    def _validate_response(self, response: requests.Response):
        """
        Checks if the response indicates an authentication failure.

        A common failure mode is receiving the Azure DevOps sign-in page
        in the response body, which indicates an invalid or expired PAT.

        Args:
            response (requests.Response): The HTTP response object.

        Raises:
            AdoAuthenticationError: If the response contains the sign-in page.
        """
        if "Sign In" in response.text:
            logger.error(
                "Authentication failed: Response contains sign-in page. "
                f"Response text: {response.text[:200]}..." # Removed newline character
            )
            raise AdoAuthenticationError(
                "Authentication failed. The response contained a sign-in page, "
                "which likely means the Personal Access Token (PAT) is invalid or expired."
            )

    def _send_request(self, method: str, url: str, **kwargs):
        """
        Sends an authenticated request to the Azure DevOps API.

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
        Verifies that the provided credentials are valid.

        This is done by making a lightweight request to a known API endpoint.

        Returns:
            bool: True if the authentication is successful.

        Raises:
            AdoAuthenticationError: If the authentication check fails due to
                an invalid token or other request-related issues.
        """
        # Use a simple, lightweight endpoint to verify the connection.
        # Listing top 1 project is a good candidate.
        url = f"{self.organization_url}/_apis/projects?api-version=7.2-preview.4&$top=1"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            self._validate_response(response)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication check failed with an exception: {e}")
            raise AdoAuthenticationError(f"Authentication check failed: {e}") from e

    def list_projects(self) -> list[dict]:
        """
        Retrieves a list of projects in the organization.

        Returns:
            list[dict]: A list of dictionaries, where each dictionary
                        represents a project.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
        """
        url = f"{self.organization_url}/_apis/projects?api-version=7.2-preview.4"
        response = self._send_request("GET", url)
        return response.get("value", [])

    def list_pipelines(self, project_id: str) -> list[dict]:
        """
        Retrieves a list of pipelines for a given project.

        Args:
            project_id (str): The ID of the project.

        Returns:
            list[dict]: A list of dictionaries, where each dictionary
                        represents a pipeline.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
        """
        url = f"{self.organization_url}/{project_id}/_apis/pipelines?api-version=7.2-preview.1"
        response = self._send_request("GET", url)
        return response.get("value", [])

    def get_pipeline(self, project_id: str, pipeline_id: int) -> dict:
        """
        Retrieves details for a specific pipeline.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.

        Returns:
            dict: A dictionary representing the pipeline details.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
        """
        url = f"{self.organization_url}/{project_id}/_apis/pipelines/{pipeline_id}?api-version=7.2-preview.1"
        response = self._send_request("GET", url)
        return response

    def run_pipeline(self, project_id: str, pipeline_id: int) -> dict:
        """
        Triggers a run for a specific pipeline.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.

        Returns:
            dict: A dictionary representing the pipeline run details.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
        """
        url = f"{self.organization_url}/{project_id}/_apis/pipelines/{pipeline_id}/runs?api-version=7.2-preview.1"
        response = self._send_request("POST", url, json={})
        return response

    def get_pipeline_run(self, project_id: str, run_id: int) -> dict:
        """
        Retrieves details for a specific pipeline run.

        Args:
            project_id (str): The ID of the project.
            run_id (int): The ID of the pipeline run.

        Returns:
            dict: A dictionary representing the pipeline run details.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
        """
        url = f"{self.organization_url}/{project_id}/_apis/pipelines/runs/{run_id}?api-version=7.2-preview.1"
        response = self._send_request("GET", url)
        return response
