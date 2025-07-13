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

# Global container for the ADO client
client_container = {
    'client': None,
}

def initialize_ado_client(org_url=None):
    """
    Initializes the Azure DevOps client. If org_url is not provided, it uses
    the ADO_ORGANIZATION_URL environment variable.
    """
    if not org_url:
        org_url = os.environ.get("ADO_ORGANIZATION_URL")
    
    if not org_url:
        return None, "ADO_ORGANIZATION_URL is not set."

    try:
        client = AdoClient(organization_url=org_url)
        client.check_authentication()
        logger.info(f"✅ Azure DevOps client initialized and authenticated successfully for {org_url}.")
        return client, None
    except (ValueError, AdoAuthenticationError) as e:
        error_message = f"Authentication check failed: {e}"
        logger.warning(f"⚠️ Could not initialize Azure DevOps client for {org_url}. Reason: {error_message}")
        return None, error_message

@mcp.tool
def set_ado_organization(organization_url: str) -> dict:
    """
    Switches the active Azure DevOps organization for the MCP server.
    If the switch fails, the client is invalidated.
    """
    logger.info(f"Attempting to switch to ADO organization: {organization_url}")
    
    new_client, error_message = initialize_ado_client(org_url=organization_url)
    
    if new_client:
        client_container['client'] = new_client
        logger.info(f"Successfully switched to organization: {organization_url}")
        return {"result": True}
    else:
        logger.error(f"Failed to switch to organization: {organization_url}. Invalidating client.")
        client_container['client'] = None
        raise AdoAuthenticationError(f"Authentication check failed: {error_message}")

# Initial client setup
client_container['client'], _ = initialize_ado_client(org_url=os.environ.get("ADO_ORGANIZATION_URL"))

from ado import tools
tools.register_ado_tools(mcp, client_container)

if __name__ == "__main__":  # pragma: no cover
    mcp.run()
