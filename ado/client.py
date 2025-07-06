import os
import requests
from base64 import b64encode


class AdoClient:
    def __init__(self, organization_url: str):
        self.organization_url = organization_url
        pat = os.environ.get("AZURE_DEVOPS_EXT_PAT")
        if not pat:
            raise ValueError("AZURE_DEVOPS_EXT_PAT environment variable not set.")

        # The PAT needs to be Base64 encoded for the Basic auth header.
        # The username is empty, so we prepend a colon to the PAT.
        encoded_pat = b64encode(f":{pat}".encode("ascii")).decode("ascii")

        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {encoded_pat}"
        }

    def _send_request(self, method: str, url: str, **kwargs):
        try:
            response = requests.request(method, url, headers=self.headers, **kwargs)
            # This will raise an HTTPError if the response was an HTTP error (4xx or 5xx)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            # This is the key change for better debugging.
            # The response body from the server often contains a detailed error message.
            error_details = http_err.response.text
            print(f"\n--- HTTP Error Details ---")
            print(f"Error: {http_err}")
            print(f"API Response Body: {error_details}")
            print(f"--------------------------\n")
            raise  # Re-raise the exception after logging
        except requests.exceptions.RequestException as err:
            # This catches other network-related errors (e.g., DNS failure, refused connection)
            print(f"An unexpected network error occurred: {err}")
            raise

    def check_authentication(self):
        """Verifies authentication by making a simple API call."""
        url = f"{self.organization_url}/_apis/ConnectionData?api-version=7.1-preview"
        return self._send_request("GET", url)
