import os
import requests
from base64 import b64encode
import logging
from .errors import AdoAuthenticationError

logger = logging.getLogger(__name__)

class AdoClient:
    def __init__(self, organization_url: str):
        self.organization_url = organization_url
        pat = os.environ.get("AZURE_DEVOPS_EXT_PAT")
        if not pat:
            raise ValueError("AZURE_DEVOPS_EXT_PAT environment variable not set.")

        encoded_pat = b64encode(f":{pat}".encode("ascii")).decode("ascii")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {encoded_pat}"
        }
        logger.info("AdoClient initialized.")

    def _validate_response(self, response: requests.Response):
        """Checks if the response is the sign-in page."""
        if "Sign In" in response.text:
            logger.error(
                "Authentication failed: Response contains sign-in page. "
                f"Response text: '{response.text[:200]}...'"
            )
            raise AdoAuthenticationError(
                "Authentication failed. The response contained a sign-in page, "
                "which likely means the Personal Access Token (PAT) is invalid or expired."
            )

    def _send_request(self, method: str, url: str, **kwargs):
        """
        Sends an authenticated request and returns the parsed JSON response.
        """
        try:
            response = requests.request(method, url, headers=self.headers, **kwargs)
            self._validate_response(response)
            response.raise_for_status()
            if not response.content:
                return None
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            logger.error(f"HTTP Error: {http_err} - Response Body: {http_err.response.text}")
            raise
        except requests.exceptions.RequestException as err:
            logger.error(f"An unexpected network error occurred: {err}")
            raise

    def check_authentication(self) -> bool:
        """
        Verifies authentication. Returns True if successful.
        Raises AdoAuthenticationError on failure.
        """
        url = f"{self.organization_url}/_apis/projects?api-version=7.2-preview.4&$top=1"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            self._validate_response(response)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication check failed with an exception: {e}")
            # Re-raise as our custom exception for consistency
            raise AdoAuthenticationError(f"Authentication check failed: {e}") from e
