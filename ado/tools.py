import logging
from typing import List
from ado.errors import AdoAuthenticationError
from ado.models import Project, Pipeline, CreatePipelineRequest, ConfigurationType, PipelineConfiguration

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
    def list_pipelines(project_id: str) -> List[Pipeline]:
        """
        Lists all pipelines in a given Azure DevOps project.

        Args:
            project_id (str): The ID of the project.

        Returns:
            List[Pipeline]: A list of Pipeline objects.
        """
        ado_client_instance = client_container.get('client')
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return []
        pipelines_response = ado_client_instance.list_pipelines(project_id)
        logger.info(f"Retrieved {len(pipelines_response)} pipelines for project {project_id}")
        return pipelines_response

    @mcp_instance.tool
    def create_pipeline(project_id: str, name: str, configuration_type: str = "yaml", folder: str = None) -> Pipeline:
        """
        Creates a new pipeline in a given Azure DevOps project.

        Args:
            project_id (str): The ID of the project.
            name (str): The name of the pipeline.
            configuration_type (str): The type of configuration (yaml, designerJson, etc.). Defaults to "yaml".
            folder (str, optional): The folder to create the pipeline in.

        Returns:
            Pipeline: The created pipeline object.
        """
        ado_client_instance = client_container.get('client')
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None
        
        try:
            config_type = ConfigurationType(configuration_type)
        except ValueError:
            logger.error(f"Invalid configuration type: {configuration_type}")
            config_type = ConfigurationType.YAML
        
        request = CreatePipelineRequest(
            name=name,
            folder=folder,
            configuration=PipelineConfiguration(type=config_type)
        )
        
        return ado_client_instance.create_pipeline(project_id, request)

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
