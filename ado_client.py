import os
import requests
from pydantic import BaseModel, Field

class Pipeline(BaseModel):
    id: int
    name: str
    folder: str | None = None

class AdoClient:
    def __init__(self, organization_url: str):
        self.organization_url = organization_url
        self.pat = os.environ.get("ADO_PAT")
        if not self.pat:
            raise ValueError("ADO_PAT environment variable not set.")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {self.pat}"
        }

    def _send_request(self, method: str, url: str, **kwargs):
        response = requests.request(method, url, headers=self.headers, **kwargs)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()

    def check_authentication(self):
        """Verifies authentication by making a simple API call."""
        url = f"{self.organization_url}/_apis/ConnectionData"
        return self._send_request("GET", url)

    def list_pipelines(self, project_name: str):
        """Lists all pipelines in a given Azure DevOps project."""
        url = f"{self.organization_url}/{project_name}/_apis/pipelines?api-version=7.1"
        return self._send_request("GET", url)
