import logging
from typing import List, Optional
from ado.errors import AdoAuthenticationError
from ado.models import Project, Pipeline, CreatePipelineRequest, ConfigurationType, PipelineConfiguration, Repository, ServiceConnection, PipelineRun, PipelinePreviewRequest, PreviewRun, TimelineResponse, StepFailure, FailureSummary, LogCollection

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
    def create_pipeline(
        project_id: str, 
        name: str, 
        yaml_path: str,
        repository_name: str,
        service_connection_id: str,
        configuration_type: str = "yaml", 
        folder: str = None,
        repository_type: str = "gitHub"
    ) -> Pipeline:
        """
        Creates a new YAML pipeline in a given Azure DevOps project.

        Args:
            project_id (str): The ID of the project.
            name (str): The name of the pipeline.
            yaml_path (str): The path to the YAML file in the repository.
            repository_name (str): The full name of the repository (e.g., "owner/repo").
            service_connection_id (str): The ID of the service connection to the repository.
            configuration_type (str): The type of configuration (yaml, designerJson, etc.). Defaults to "yaml".
            folder (str, optional): The folder to create the pipeline in.
            repository_type (str): The type of repository (gitHub, azureReposGit, etc.). Defaults to "gitHub".

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
        
        # Create the repository configuration
        repository = Repository(
            fullName=repository_name,
            connection=ServiceConnection(id=service_connection_id),
            type=repository_type
        )
        
        # Create the pipeline configuration
        configuration = PipelineConfiguration(
            type=config_type,
            path=yaml_path,
            repository=repository
        )
        
        request = CreatePipelineRequest(
            name=name,
            folder=folder,
            configuration=configuration
        )
        
        return ado_client_instance.create_pipeline(project_id, request)

    @mcp_instance.tool
    def list_service_connections(project_id: str) -> list:
        """
        Lists service connections for a given Azure DevOps project.

        Args:
            project_id (str): The ID of the project.

        Returns:
            list: A list of service connection objects.
        """
        ado_client_instance = client_container.get('client')
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return []
        
        connections = ado_client_instance.list_service_connections(project_id)
        logger.info(f"Retrieved {len(connections)} service connections for project {project_id}")
        return connections

    @mcp_instance.tool
    def delete_pipeline(project_id: str, pipeline_id: int) -> bool:
        """
        Deletes a pipeline from a given Azure DevOps project.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline to delete.

        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        ado_client_instance = client_container.get('client')
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return False
        
        try:
            result = ado_client_instance.delete_pipeline(project_id, pipeline_id)
            if result:
                logger.info(f"Successfully deleted pipeline {pipeline_id} from project {project_id}")
            else:
                logger.warning(f"Failed to delete pipeline {pipeline_id} from project {project_id}")
            return result
        except Exception as e:
            logger.error(f"Error deleting pipeline {pipeline_id}: {e}")
            return False

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
    def run_pipeline(project_id: str, pipeline_id: int) -> Optional[PipelineRun]:
        """
        Triggers a run for a specific pipeline in an Azure DevOps project.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.

        Returns:
            Optional[PipelineRun]: A PipelineRun object representing the pipeline run details, or None if client unavailable.
        """
        ado_client_instance = client_container.get('client')
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None
        return ado_client_instance.run_pipeline(project_id, pipeline_id)

    @mcp_instance.tool
    def get_pipeline_run(project_id: str, pipeline_id: int, run_id: int) -> Optional[PipelineRun]:
        """
        Retrieves details for a specific pipeline run in an Azure DevOps project.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.
            run_id (int): The ID of the pipeline run.

        Returns:
            Optional[PipelineRun]: A PipelineRun object representing the pipeline run details, or None if client unavailable.
        """
        ado_client_instance = client_container.get('client')
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None
        return ado_client_instance.get_pipeline_run(project_id, pipeline_id, run_id)

    @mcp_instance.tool
    def preview_pipeline(
        project_id: str, 
        pipeline_id: int,
        yaml_override: Optional[str] = None,
        variables: Optional[dict] = None,
        template_parameters: Optional[dict] = None,
        stages_to_skip: Optional[List[str]] = None
    ) -> Optional[PreviewRun]:
        """
        Previews a pipeline without executing it, returning the final YAML and other preview information.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.
            yaml_override (Optional[str]): Optional YAML override for testing different configurations.
            variables (Optional[dict]): Optional runtime variables for the preview.
            template_parameters (Optional[dict]): Optional template parameters for the preview.
            stages_to_skip (Optional[List[str]]): Optional list of stage names to skip during preview.

        Returns:
            Optional[PreviewRun]: A PreviewRun object representing the pipeline preview details, or None if client unavailable.
        """
        ado_client_instance = client_container.get('client')
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None
        
        # Build the preview request
        request = PipelinePreviewRequest(
            previewRun=True,
            yamlOverride=yaml_override,
            variables=variables,
            templateParameters=template_parameters,
            stagesToSkip=stages_to_skip
        )
        
        return ado_client_instance.preview_pipeline(project_id, pipeline_id, request)

    @mcp_instance.tool
    def get_pipeline_failure_summary(
        project_id: str, 
        pipeline_id: int, 
        run_id: int
    ) -> Optional[FailureSummary]:
        """
        Gets a comprehensive summary of pipeline failures, identifying root causes and affected components.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.
            run_id (int): The ID of the pipeline run.

        Returns:
            Optional[FailureSummary]: Detailed failure analysis including root cause tasks and hierarchy failures, or None if client unavailable.
        """
        ado_client_instance = client_container.get('client')
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None
        
        return ado_client_instance.get_pipeline_failure_summary(project_id, pipeline_id, run_id)

    @mcp_instance.tool
    def get_failed_step_logs(
        project_id: str, 
        pipeline_id: int, 
        run_id: int,
        step_name: Optional[str] = None
    ) -> Optional[List[StepFailure]]:
        """
        Gets detailed log information for failed steps, optionally filtered by step name.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.
            run_id (int): The ID of the pipeline run.
            step_name (Optional[str]): Filter to specific step name (case-insensitive partial match).

        Returns:
            Optional[List[StepFailure]]: List of failed steps with their log content, or None if client unavailable.
        """
        ado_client_instance = client_container.get('client')
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None
        
        return ado_client_instance.get_failed_step_logs(project_id, pipeline_id, run_id, step_name)

    @mcp_instance.tool
    def get_pipeline_timeline(
        project_id: str, 
        pipeline_id: int, 
        run_id: int
    ) -> Optional[TimelineResponse]:
        """
        Gets the build timeline for a pipeline run, showing status of all stages, jobs, and tasks.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.
            run_id (int): The ID of the pipeline run.

        Returns:
            Optional[TimelineResponse]: Timeline showing status of all pipeline components, or None if client unavailable.
        """
        ado_client_instance = client_container.get('client')
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None
        
        return ado_client_instance.get_pipeline_timeline(project_id, pipeline_id, run_id)

    @mcp_instance.tool
    def list_pipeline_logs(
        project_id: str, 
        pipeline_id: int, 
        run_id: int
    ) -> Optional[LogCollection]:
        """
        Lists all logs for a specific pipeline run.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.
            run_id (int): The ID of the pipeline run.

        Returns:
            Optional[LogCollection]: Collection of log entries for the pipeline run, or None if client unavailable.
        """
        ado_client_instance = client_container.get('client')
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None
        
        return ado_client_instance.list_pipeline_logs(project_id, pipeline_id, run_id)

    @mcp_instance.tool
    def get_log_content_by_id(
        project_id: str, 
        pipeline_id: int, 
        run_id: int,
        log_id: int
    ) -> Optional[str]:
        """
        Gets the content of a specific log from a pipeline run.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.
            run_id (int): The ID of the pipeline run.
            log_id (int): The ID of the specific log.

        Returns:
            Optional[str]: The log content as a string, or None if client unavailable.
        """
        ado_client_instance = client_container.get('client')
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None
        
        return ado_client_instance.get_log_content_by_id(project_id, pipeline_id, run_id, log_id)
