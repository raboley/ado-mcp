import os
import requests
from base64 import b64encode


# This standalone function is no longer needed and should be removed.
# Its logic is now correctly placed inside the AdoClient class.

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
        """
        Sends an authenticated request and returns the parsed JSON response.
        This method is for standard API calls where a JSON body is expected.
        """
        try:
            response = requests.request(method, url, headers=self.headers, **kwargs)
            response.raise_for_status()

            # If the response has no content (e.g., 204 No Content),
            # return None instead of trying to parse an empty body.
            if not response.content:
                return None

            return response.json()
        except requests.exceptions.HTTPError as http_err:
            error_details = http_err.response.text
            print(f"\n--- HTTP Error Details ---")
            print(f"Error: {http_err}")
            print(f"API Response Body: {error_details}")
            print(f"--------------------------\n")
            raise
        except requests.exceptions.RequestException as err:
            print(f"An unexpected network error occurred: {err}")
            raise

    def check_authentication(self) -> bool:
        """
        Verifies authentication by specifically checking for the ADO sign-in page.

        This is a special case because a failed auth can return an HTML login page
        with a 203 status code instead of a 401 error.
        """
        # Use a lightweight endpoint for the check.
        url = f"{self.organization_url}/_apis/projects?api-version=7.2-preview.4&$top=1"
        try:
            # Make a direct request to inspect the raw response, bypassing _send_request.
            response = requests.get(url, headers=self.headers, timeout=10)

            # Check for the login page text in the response body.
            if "Sign In" in response.text:
                print("Authentication failed: Response body contains the ADO sign-in page.")
                return False

            # If we get here, it's not a login page. Now check for other errors.
            response.raise_for_status()

            # If no exceptions were raised, authentication is successful.
            return True

        except requests.exceptions.RequestException as e:
            # This gracefully catches any failure: HTTP errors from raise_for_status(),
            # connection errors, timeouts, etc.
            print(f"Authentication check failed with an exception: {e}")
            return False
