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
        self.pat = os.environ.get("AZURE_DEVOPS_EXT_PAT")
        if not self.pat:
            raise ValueError("AZURE_DEVOPS_EXT_PAT environment variable not set.")
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

    def list_pipelines(self, project_name: str) -> list[Pipeline]:
        """Lists all pipelines in a given Azure DevOps project."""
        url = f"{self.organization_url}/{project_name}/_apis/pipelines?api-version=7.2-preview.1"
        response_data = self._send_request("GET", url)
        return [Pipeline(**item) for item in response_data.get("value", [])]
