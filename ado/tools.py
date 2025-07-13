import logging
from ado.errors import AdoAuthenticationError
from ado.models import Project

logger = logging.getLogger(__name__)

def register_ado_tools(mcp_instance, client_container):
    """
    Registers Azure DevOps related tools with the FastMCP instance.

    Args:
        mcp_instance: The FastMCP instance to register tools with.
        client_container (dict): A dictionary holding the AdoClient instance,
            allowing the client to be updated dynamically.
    """

    @mcp_instance.tool
    def check_ado_authentication() -> bool:
        """
        Verifies that the connection and authentication to Azure DevOps are successful.

        Returns:
            bool: True if authentication is successful, False otherwise.
        """
        ado_client_instance = client_container.get('client')
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return False
        return ado_client_instance.check_authentication()

    @mcp_instance.tool
    def list_projects() -> list[Project]:
        """
        Lists all projects in the Azure DevOps organization.

        Returns:
            list[Project]: A list of Project objects.
        """
        ado_client_instance = client_container.get('client')
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return []
        return ado_client_instance.list_projects()

    @mcp_instance.tool
    def list_pipelines(project_id: str) -> list[dict]:
        """
        Lists all pipelines in a given Azure DevOps project.

        Args:
            project_id (str): The ID of the project.

        Returns:
            list[dict]: A list of dictionaries, where each dictionary
                        represents a pipeline.
        """
        ado_client_instance = client_container.get('client')
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return []
        pipelines_response = ado_client_instance.list_pipelines(project_id)
        return pipelines_response

    @mcp_instance.tool
    def get_pipeline(project_id: str, pipeline_id: int) -> dict:
        """
        Retrieves details for a specific pipeline in an Azure DevOps project.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.

        Returns:
            dict: A dictionary representing the pipeline details.
        """
        ado_client_instance = client_container.get('client')
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return {}
        return ado_client_instance.get_pipeline(project_id, pipeline_id)

    @mcp_instance.tool
    def run_pipeline(project_id: str, pipeline_id: int) -> dict:
        """
        Triggers a run for a specific pipeline in an Azure DevOps project.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.

        Returns:
            dict: A dictionary representing the pipeline run details.
        """
        ado_client_instance = client_container.get('client')
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return {}
        return ado_client_instance.run_pipeline(project_id, pipeline_id)

    @mcp_instance.tool
    def get_pipeline_run(project_id: str, run_id: int) -> dict:
        """
        Retrieves details for a specific pipeline run in an Azure DevOps project.

        Args:
            project_id (str): The ID of the project.
            run_id (int): The ID of the pipeline run.

        Returns:
            dict: A dictionary representing the pipeline run details.
        """
        ado_client_instance = client_container.get('client')
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return {}
        return ado_client_instance.get_pipeline_run(project_id, run_id)
