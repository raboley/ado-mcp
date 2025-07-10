import os
import logging
from fastmcp import FastMCP
from ado.client import AdoClient
from ado.errors import AdoAuthenticationError

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="ado-mcp",
    version="0.1.0"
)

# Initialize the ADO client within a dedicated function for clarity and error handling.
def initialize_ado_client():
    """
    Initializes and authenticates the Azure DevOps client.

    Returns:
        AdoClient: An initialized and authenticated client instance.
        None: If initialization fails due to missing configuration or authentication errors.
    """
    try:
        org_url = os.environ.get("ADO_ORGANIZATION_URL")
        if not org_url:
            raise ValueError("ADO_ORGANIZATION_URL environment variable is not set.")

        client = AdoClient(organization_url=org_url)
        client.check_authentication()
        logger.info("✅ Azure DevOps client initialized and authenticated successfully.")
        return client
    except (ValueError, AdoAuthenticationError) as e:
        logger.warning(f"⚠️ Could not initialize Azure DevOps client. ADO features will be disabled. Reason: {e}")
        return None

# Initialize the client on server startup.
client_container = {'client': None}

def initialize_ado_client(org_url=None):
    try:
        if not org_url:
            org_url = os.environ.get("ADO_ORGANIZATION_URL")
        if not org_url:
            return None, "ADO_ORGANIZATION_URL environment variable is not set."

        client = AdoClient(organization_url=org_url)
        client.check_authentication()
        logger.info(f"✅ Azure DevOps client initialized and authenticated successfully for {org_url}.")
        return client, None
    except (ValueError, AdoAuthenticationError) as e:
        error_message = f"Authentication check failed: {e}"
        logger.warning(f"⚠️ Could not initialize Azure DevOps client for {org_url}. ADO features will be disabled. Reason: {error_message}")
        return None, error_message

@mcp.tool
def set_ado_organization(organization_url: str) -> dict:
    """
    Switches the active Azure DevOps organization for the MCP server.

    Args:
        organization_url (str): The URL of the new Azure DevOps organization.
            Example: 'https://dev.azure.com/your-org'

    Returns:
        dict: A dictionary with 'result' (bool) and optionally 'error' (str) keys.
    """
    logger.info(f"Attempting to switch to ADO organization: {organization_url}")
    new_client, error_message = initialize_ado_client(org_url=organization_url)
    if new_client:
        client_container['client'] = new_client
        return {"result": True}
    else:
        logger.error(f"Failed to switch to organization: {organization_url}. Reason: {error_message}")
        client_container['client'] = None # Explicitly set to None on failure
        raise AdoAuthenticationError(error_message)

client_container['client'], _ = initialize_ado_client()

from ado import tools
tools.register_ado_tools(mcp, client_container)

if __name__ == "__main__":  # pragma: no cover
    mcp.run()
