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
ado_client = initialize_ado_client()

# Import tools to register them with the MCP server
from ado import tools

# Register tools with the MCP server
tools.register_ado_tools(mcp, ado_client)

if __name__ == "__main__":  # pragma: no cover
    mcp.run()
