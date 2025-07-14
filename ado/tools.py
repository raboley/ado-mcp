import logging

from ado.models import (
    ConfigurationType,
    CreatePipelineRequest,
    FailureSummary,
    LogCollection,
    Pipeline,
    PipelineConfiguration,
    PipelineOutcome,
    PipelinePreviewRequest,
    PipelineRun,
    PreviewRun,
    Project,
    Repository,
    ServiceConnection,
    StepFailure,
    TimelineResponse,
)

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
        ado_client_instance = client_container.get("client")
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
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return []
        return ado_client_instance.list_projects()

    @mcp_instance.tool
    def list_pipelines(project_id: str) -> list[Pipeline]:
        """
        Lists all pipelines in a given Azure DevOps project.

        Args:
            project_id (str): The ID of the project.

        Returns:
            List[Pipeline]: A list of Pipeline objects.
        """
        ado_client_instance = client_container.get("client")
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
        repository_type: str = "gitHub",
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
        ado_client_instance = client_container.get("client")
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
            type=repository_type,
        )

        # Create the pipeline configuration
        configuration = PipelineConfiguration(
            type=config_type, path=yaml_path, repository=repository
        )

        request = CreatePipelineRequest(name=name, folder=folder, configuration=configuration)

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
        ado_client_instance = client_container.get("client")
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
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return False

        try:
            result = ado_client_instance.delete_pipeline(project_id, pipeline_id)
            if result:
                logger.info(
                    f"Successfully deleted pipeline {pipeline_id} from project {project_id}"
                )
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
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return {}
        return ado_client_instance.get_pipeline(project_id, pipeline_id)

    @mcp_instance.tool
    def get_build_by_id(project_id: str, build_id: int) -> dict:
        """
        🔍 MAP BUILD ID TO PIPELINE: Retrieves build details and extracts pipeline information.

        ⚡ USE THIS WHEN: User provides an Azure DevOps URL with buildId parameter

        CRITICAL: buildId in URLs is actually a RUN ID, not a pipeline ID!
        This tool maps run_id → pipeline_id so you can use other pipeline tools.

        Example: URL has buildId=324 → use this tool → get pipeline_id=84
        Then use pipeline_id=84 with other tools like get_pipeline_failure_summary.

        Args:
            project_id (str): The project UUID (get from list_projects if needed)
            build_id (int): The buildId from Azure DevOps URL (this is actually a run_id)

        Returns:
            dict: Build details with definition.id (pipeline_id) and definition.name
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return {}
        return ado_client_instance.get_build_by_id(project_id, build_id)

    @mcp_instance.tool
    def run_pipeline(project_id: str, pipeline_id: int) -> PipelineRun | None:
        """
        Triggers a run for a specific pipeline in an Azure DevOps project.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.

        Returns:
            Optional[PipelineRun]: A PipelineRun object representing the pipeline run details, or None if client unavailable.
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None
        return ado_client_instance.run_pipeline(project_id, pipeline_id)

    @mcp_instance.tool
    def get_pipeline_run(project_id: str, pipeline_id: int, run_id: int) -> PipelineRun | None:
        """
        Retrieves details for a specific pipeline run in an Azure DevOps project.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.
            run_id (int): The ID of the pipeline run.

        Returns:
            Optional[PipelineRun]: A PipelineRun object representing the pipeline run details, or None if client unavailable.
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None
        return ado_client_instance.get_pipeline_run(project_id, pipeline_id, run_id)

    @mcp_instance.tool
    def preview_pipeline(
        project_id: str,
        pipeline_id: int,
        yaml_override: str | None = None,
        variables: dict | None = None,
        template_parameters: dict | None = None,
        stages_to_skip: list[str] | None = None,
    ) -> PreviewRun | None:
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
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None

        # Build the preview request
        request = PipelinePreviewRequest(
            previewRun=True,
            yamlOverride=yaml_override,
            variables=variables,
            templateParameters=template_parameters,
            stagesToSkip=stages_to_skip,
        )

        return ado_client_instance.preview_pipeline(project_id, pipeline_id, request)

    @mcp_instance.tool
    def get_pipeline_failure_summary(
        project_id: str, pipeline_id: int, run_id: int, max_lines: int = 100
    ) -> FailureSummary | None:
        """
        🔥 ANALYZE FAILED BUILDS: Get comprehensive failure analysis with root causes.

        ⚡ USE THIS WHEN: User wants to know why a build failed

        This tool provides intelligent failure analysis:
        - Root cause tasks (actual failing steps)
        - Hierarchy failures (jobs that failed due to child failures)
        - Categorized error information
        - Log content for failing steps (limited to last max_lines by default)

        IMPORTANT: Use get_build_by_id first if you only have a buildId from URL!

        Args:
            project_id (str): The project UUID
            pipeline_id (int): Pipeline definition ID (NOT the buildId from URL!)
            run_id (int): The run/build ID (buildId from URL)
            max_lines (int): Maximum number of lines to return from the end of each log (default: 100).
                           Set to 0 or negative to return all lines.

        Returns:
            FailureSummary: Analysis with root_cause_tasks, hierarchy_failures, total_failed_steps
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None

        return ado_client_instance.get_pipeline_failure_summary(
            project_id, pipeline_id, run_id, max_lines
        )

    @mcp_instance.tool
    def get_failed_step_logs(
        project_id: str,
        pipeline_id: int,
        run_id: int,
        step_name: str | None = None,
        max_lines: int = 100,
    ) -> list[StepFailure] | None:
        """
        Gets detailed log information for failed steps, optionally filtered by step name.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.
            run_id (int): The ID of the pipeline run.
            step_name (Optional[str]): Filter to specific step name (case-insensitive partial match).
            max_lines (int): Maximum number of lines to return from the end of each log (default: 100).
                           Set to 0 or negative to return all lines.

        Returns:
            Optional[List[StepFailure]]: List of failed steps with their log content, or None if client unavailable.
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None

        return ado_client_instance.get_failed_step_logs(
            project_id, pipeline_id, run_id, step_name, max_lines
        )

    @mcp_instance.tool
    def get_pipeline_timeline(
        project_id: str, pipeline_id: int, run_id: int
    ) -> TimelineResponse | None:
        """
        Gets the build timeline for a pipeline run, showing status of all stages, jobs, and tasks.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.
            run_id (int): The ID of the pipeline run.

        Returns:
            Optional[TimelineResponse]: Timeline showing status of all pipeline components, or None if client unavailable.
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None

        return ado_client_instance.get_pipeline_timeline(project_id, pipeline_id, run_id)

    @mcp_instance.tool
    def list_pipeline_logs(project_id: str, pipeline_id: int, run_id: int) -> LogCollection | None:
        """
        Lists all logs for a specific pipeline run.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.
            run_id (int): The ID of the pipeline run.

        Returns:
            Optional[LogCollection]: Collection of log entries for the pipeline run, or None if client unavailable.
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None

        return ado_client_instance.list_pipeline_logs(project_id, pipeline_id, run_id)

    @mcp_instance.tool
    def get_log_content_by_id(
        project_id: str, pipeline_id: int, run_id: int, log_id: int, max_lines: int = 100
    ) -> str | None:
        """
        Gets the content of a specific log from a pipeline run.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.
            run_id (int): The ID of the pipeline run.
            log_id (int): The ID of the specific log.
            max_lines (int): Maximum number of lines to return from the end of the log (default: 100).
                           Set to 0 or negative to return all lines.

        Returns:
            Optional[str]: The log content as a string, or None if client unavailable.
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None

        return ado_client_instance.get_log_content_by_id(
            project_id, pipeline_id, run_id, log_id, max_lines
        )

    @mcp_instance.tool
    def run_pipeline_and_get_outcome(
        project_id: str, pipeline_id: int, timeout_seconds: int = 300, max_lines: int = 100
    ) -> PipelineOutcome | None:
        """
        🚀 RUN PIPELINE & WAIT: Execute pipeline and get complete outcome analysis.

        ⚡ USE THIS WHEN: User wants to run a pipeline and see results immediately

        This is the most comprehensive execution tool that:
        1. Starts the pipeline
        2. Waits for completion (up to timeout)
        3. Returns success/failure with detailed analysis
        4. Includes failure summary and logs if it fails (limited to last max_lines by default)

        Perfect for: "Run the pipeline and tell me what happens"

        Args:
            project_id (str): The project UUID
            pipeline_id (int): Pipeline definition ID (use find_pipeline_by_name if needed)
            timeout_seconds (int): Max wait time (default: 300s = 5 minutes)
            max_lines (int): Maximum number of lines to return from the end of each log (default: 100).
                           Set to 0 or negative to return all lines.

        Returns:
            PipelineOutcome: Complete results with pipeline_run, success flag, failure_summary, execution_time
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None

        return ado_client_instance.run_pipeline_and_get_outcome(
            project_id, pipeline_id, timeout_seconds, max_lines
        )
