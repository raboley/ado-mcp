import logging
from ado.errors import AdoAuthenticationError
from ado.models import Project

logger = logging.getLogger(__name__)

def register_ado_tools(mcp_instance, ado_client_instance):
    """
    Registers Azure DevOps related tools with the FastMCP instance.

    Args:
        mcp_instance: The FastMCP instance to register tools with.
        ado_client_instance: The AdoClient instance to use for API calls.
    """

    @mcp_instance.tool
    def check_ado_authentication() -> bool:
        """
        Verifies that the connection and authentication to Azure DevOps are successful.

        Returns:
            bool: True if authentication is successful, False otherwise.
        """
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return False
        try:
            return ado_client_instance.check_authentication()
        except AdoAuthenticationError as e:
            logger.error(f"ADO authentication check failed: {e}")
            return False

    @mcp_instance.tool
    def list_projects() -> list[Project]:
        """
        Lists all projects in the Azure DevOps organization.

        Returns:
            list[Project]: A list of Project objects.
        """
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return []
        return ado_client_instance.list_projects()