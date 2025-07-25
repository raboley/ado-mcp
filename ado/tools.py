import logging
import os
from typing import Any

from ado.enhanced_tools.projects import EnhancedProjectTools
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
    RunResourcesParameters,
    ServiceConnection,
    StepFailure,
    TimelineResponse,
)
from ado.work_items.tools import register_work_item_tools

logger = logging.getLogger(__name__)


def register_ado_tools(mcp_instance, client_container):
    """
    Registers Azure DevOps related tools with the FastMCP instance.

    Args:
        mcp_instance: The FastMCP instance to register tools with.
        client_container (dict): A dictionary holding the AdoClient instance,
            allowing the client to be updated dynamically.
    """

    # Helper functions to reduce code duplication
    def get_client_or_error(error_return=None):
        """Get ADO client instance or return error value."""
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None, error_return
        return ado_client_instance, None

    def get_pipeline_ids_with_client_check(project_name: str, pipeline_name: str):
        """Get client and resolve pipeline IDs from names."""
        client, error_return = get_client_or_error()
        if client is None:
            return None, None, None

        try:
            project_id, pipeline_id = client._lookups.get_pipeline_ids(project_name, pipeline_name)
            return client, project_id, pipeline_id
        except Exception as e:
            logger.error(f"Error resolving pipeline IDs: {e}")
            return None, None, None

    @mcp_instance.tool
    def check_ado_authentication() -> bool:
        """
        Verifies that the connection and authentication to Azure DevOps are successful.

        Returns:
            bool: True if authentication is successful, False otherwise.
        """
        ado_client_instance, error_return = get_client_or_error(False)
        if ado_client_instance is None:
            return error_return
        return ado_client_instance.check_authentication()

    @mcp_instance.tool
    def list_projects() -> list[Project]:
        """
        Lists all projects in the Azure DevOps organization.

        Returns:
            List[Project]: A list of Project objects.
        """
        ado_client_instance, error_return = get_client_or_error([])
        if ado_client_instance is None:
            return error_return
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
    def delete_pipeline(project_name: str, pipeline_name: str) -> bool:
        """
        Deletes a pipeline from a given Azure DevOps project.

        Args:
            project_name (str): The name of the project (supports fuzzy matching).
            pipeline_name (str): The name of the pipeline to delete (supports fuzzy matching).

        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return False

        try:
            # Get project and pipeline IDs using name lookup
            project_id, pipeline_id = ado_client_instance._lookups.get_pipeline_ids(
                project_name, pipeline_name
            )
            result = ado_client_instance.delete_pipeline(project_id, pipeline_id)
            if result:
                # Invalidate pipeline cache after successful deletion
                from .cache import ado_cache

                ado_cache.invalidate_pipelines(project_id)
                logger.info(
                    f"Successfully deleted pipeline {pipeline_id} from project {project_id}"
                )
            else:
                logger.warning(f"Failed to delete pipeline {pipeline_id} from project {project_id}")
            return result
        except Exception as e:
            logger.error(f"Error deleting pipeline: {e}")
            return False

    @mcp_instance.tool
    def get_pipeline(project_name: str, pipeline_name: str) -> dict:
        """
        Retrieves details for a specific pipeline in an Azure DevOps project.

        Args:
            project_name (str): The name of the project (supports fuzzy matching).
            pipeline_name (str): The name of the pipeline (supports fuzzy matching).

        Returns:
            dict: A dictionary representing the pipeline details.
        """
        ado_client_instance, project_id, pipeline_id = get_pipeline_ids_with_client_check(
            project_name, pipeline_name
        )
        if ado_client_instance is None:
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
    def run_pipeline(
        project_name: str,
        pipeline_name: str,
        variables: dict[str, Any] | None = None,
        template_parameters: dict[str, Any] | None = None,
        branch: str | None = None,
        stages_to_skip: list[str] | None = None,
        resources: RunResourcesParameters | None = None,
    ) -> PipelineRun | None:
        """
        Start a pipeline run by name and return immediately with run details.

        NOTE: Most users want run_pipeline_and_get_outcome instead, which waits for
        completion and returns the full results. Only use this tool if you specifically
        need to start a pipeline without waiting for it to finish.

        This tool starts a pipeline and returns the run information immediately without
        waiting for completion.

        Args:
            project_name (str): Name of the Azure DevOps project
            pipeline_name (str): Name of the pipeline to run (supports fuzzy matching for typos)
            variables (dict): Runtime variables for the pipeline
                            Variables must be configured as "settable at queue time" in Azure DevOps
                            Example: {"environment": "staging", "version": "1.2.3"}
            template_parameters (dict): Template parameters for conditional pipeline logic
                                      Example: {"deployToProduction": true, "runTests": false}
            branch (str): Branch to run from (e.g. "refs/heads/main", "refs/heads/feature/new-feature")
            stages_to_skip (list): Stage names to skip (e.g. ["Security", "Performance"])
            resources (dict): Override repository branches/versions used by the pipeline
                            Example: {"repositories": {"external-repo": {"refName": "refs/heads/stable"}}}

        Returns:
            PipelineRun: Information about the started pipeline run including:
                - id: The run ID for tracking progress
                - state: Current state (usually "inProgress")
                - createdDate: When the run was created
                - url: Link to view the run in Azure DevOps

        Examples:
            # Start a simple pipeline
            run_pipeline("MyProject", "CI Pipeline")

            # Start with variables
            run_pipeline(
                "MyProject",
                "Deploy Pipeline",
                variables={"environment": "staging"}
            )
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None

        # Create request if any parameters are provided
        request = None
        if any([variables, template_parameters, branch, stages_to_skip, resources]):
            from .models import PipelineRunRequest

            request = PipelineRunRequest(
                variables=variables,
                templateParameters=template_parameters,
                branch=branch,
                stagesToSkip=stages_to_skip,
                resources=resources,
            )

        return ado_client_instance.run_pipeline_by_name(project_name, pipeline_name, request)

    @mcp_instance.tool
    def get_pipeline_run(project_name: str, pipeline_name: str, run_id: int) -> PipelineRun | None:
        """
        Retrieves details for a specific pipeline run in an Azure DevOps project.

        Args:
            project_name (str): The name of the project (supports fuzzy matching).
            pipeline_name (str): The name of the pipeline (supports fuzzy matching).
            run_id (int): The ID of the pipeline run.

        Returns:
            Optional[PipelineRun]: A PipelineRun object representing the pipeline run details, or None if client unavailable.
        """
        ado_client_instance, project_id, pipeline_id = get_pipeline_ids_with_client_check(
            project_name, pipeline_name
        )
        if ado_client_instance is None:
            return None
        return ado_client_instance.get_pipeline_run(project_id, pipeline_id, run_id)

    def _inject_github_tokens_if_needed(
        ado_client_instance, project_id: str, pipeline_id: int, resources_dict: dict | None
    ) -> dict | None:
        """
        Inject GitHub tokens for repository resources that explicitly specify RepositoryType: "gitHub".

        This function:
        1. Only injects tokens for repositories with explicit RepositoryType: "gitHub"
        2. Skips repositories without RepositoryType (assumes public repositories)
        3. Skips injection if token is already provided
        4. Logs warnings only for unsupported repository types (when RepositoryType is provided)

        Args:
            ado_client_instance: The ADO client instance (unused but kept for signature compatibility)
            project_id (str): The project ID (unused but kept for signature compatibility)
            pipeline_id (int): The pipeline ID (unused but kept for signature compatibility)
            resources_dict (Optional[dict]): The resources dictionary from user input

        Returns:
            Optional[dict]: Updated resources dictionary with GitHub tokens injected where appropriate
        """
        if not resources_dict or "repositories" not in resources_dict:
            return resources_dict

        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            logger.debug("No GITHUB_TOKEN environment variable found, skipping token injection")
            return resources_dict

        for repo_name, repo_params in resources_dict["repositories"].items():
            if not isinstance(repo_params, dict):
                continue

            repo_type = repo_params.get("RepositoryType")

            # If no RepositoryType specified, assume public repository - no token injection needed
            if not repo_type:
                logger.debug(
                    f"Repository '{repo_name}' has no RepositoryType specified, assuming public repository"
                )
                continue

            if repo_type == "gitHub":
                # Only inject if token is not already provided
                if "token" not in repo_params:
                    repo_params["token"] = github_token
                    repo_params["tokenType"] = "Basic"
                    logger.info(
                        f"Injected GitHub token for private repository '{repo_name}' (RepositoryType: gitHub)"
                    )
                else:
                    logger.debug(
                        f"Repository '{repo_name}' already has token provided, skipping injection"
                    )
            else:
                logger.warning(
                    f"Repository '{repo_name}' has unsupported RepositoryType: '{repo_type}'. Currently only 'gitHub' is supported for automatic token injection."
                )

        return resources_dict

    @mcp_instance.tool
    def preview_pipeline(
        project_name: str,
        pipeline_name: str,
        yaml_override: str | None = None,
        variables: dict[str, Any] | None = None,
        template_parameters: dict[str, Any] | None = None,
        stages_to_skip: list[str] | None = None,
        resources: RunResourcesParameters | None = None,
    ) -> PreviewRun | None:
        """
        Previews a pipeline without executing it, returning the final YAML and other preview information.

        🔧 REPOSITORY TYPE AUTHENTICATION: RepositoryType is optional for public repositories but
        required for private repositories that need authentication. Automatic token injection is
        provided for supported repository types.

        Environment tokens:
        - GitHub: GITHUB_TOKEN

        📋 SUPPORTED PRIVATE REPOSITORY TYPES:
        - "gitHub": Automatically injects GITHUB_TOKEN from environment if available

        ⚠️  UNSUPPORTED TYPES: Azure Repos, Bitbucket, and other repository types are not yet supported.

        💡 REPOSITORY RESOURCE FORMAT:

        Public repositories (no authentication needed):
        resources = {
            "repositories": {
                "repo_name": {
                    "refName": "refs/heads/branch_name"
                }
            }
        }

        Private repositories (authentication required):
        resources = {
            "repositories": {
                "repo_name": {
                    "refName": "refs/heads/branch_name",
                    "RepositoryType": "gitHub"  # Required for private repos
                }
            }
        }

        Args:
            project_name (str): The name of the project (supports fuzzy matching).
            pipeline_name (str): The name of the pipeline (supports fuzzy matching).
            yaml_override (Optional[str]): Optional YAML override for testing different configurations.
            variables (Optional[dict]): Optional runtime variables for the preview.
            template_parameters (Optional[dict]): Optional template parameters for the preview.
            stages_to_skip (Optional[List[str]]): Optional list of stage names to skip during preview.
            resources (Optional[dict]): Optional resources configuration. Each repository should include:
                       - "refName": Branch/tag reference (e.g., "refs/heads/main") [REQUIRED]
                       - "RepositoryType": Repository type (e.g., "gitHub") [REQUIRED for private repos only]
                       - "token": Authentication token [Optional - auto-injected for supported types]

        Returns:
            Optional[PreviewRun]: A PreviewRun object representing the pipeline preview details, or None if client unavailable.
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None

        # Get project and pipeline IDs using name lookup
        project_id, pipeline_id = ado_client_instance._lookups.get_pipeline_ids(
            project_name, pipeline_name
        )

        # Build the preview request - convert resources to dict if provided
        resources_dict = None
        if resources:
            resources_dict = (
                resources.dict(exclude_none=True) if hasattr(resources, "dict") else resources
            )

            # Auto-inject GitHub tokens for GitHub repositories only
            resources_dict = _inject_github_tokens_if_needed(
                ado_client_instance, project_id, pipeline_id, resources_dict
            )

        request = PipelinePreviewRequest(
            previewRun=True,
            yamlOverride=yaml_override,
            variables=variables,
            templateParameters=template_parameters,
            stagesToSkip=stages_to_skip,
            resources=resources_dict,
        )

        return ado_client_instance.preview_pipeline(project_id, pipeline_id, request)

    @mcp_instance.tool
    def get_pipeline_failure_summary(
        project_name: str, pipeline_name: str, run_id: int, max_lines: int = 100
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
            project_name (str): The name of the project (supports fuzzy matching)
            pipeline_name (str): The name of the pipeline (supports fuzzy matching)
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

        # Get project and pipeline IDs using name lookup
        project_id, pipeline_id = ado_client_instance._lookups.get_pipeline_ids(
            project_name, pipeline_name
        )

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
        project_name: str,
        pipeline_name: str,
        timeout_seconds: int = 300,
        max_lines: int = 100,
        variables: dict[str, Any] | None = None,
        template_parameters: dict[str, Any] | None = None,
        branch: str | None = None,
        stages_to_skip: list[str] | None = None,
        resources: RunResourcesParameters | None = None,
    ) -> PipelineOutcome | None:
        """
        Execute a pipeline by name and wait for completion with full result analysis.

        This is the preferred tool for running pipelines. It runs a pipeline and waits
        for it to complete, returning comprehensive results including success/failure
        status, execution time, and detailed failure analysis with logs if the pipeline fails.

        Use this when you want to run a pipeline and see what happens - which is almost
        always what you want. Only use run_pipeline if you specifically need to start
        a pipeline without waiting for results.

        Args:
            project_name (str): Name of the Azure DevOps project
            pipeline_name (str): Name of the pipeline to run (supports fuzzy matching for typos)
            timeout_seconds (int): Maximum time to wait for completion (default: 300 seconds)
            max_lines (int): Maximum log lines to return if pipeline fails (default: 100)
            variables (dict): Runtime variables for the pipeline
                            Variables must be configured as "settable at queue time" in Azure DevOps
                            Example: {"environment": "staging", "version": "1.2.3"}
            template_parameters (dict): Template parameters for conditional pipeline logic
                                      Example: {"deployToProduction": true, "runTests": false}
            branch (str): Branch to run from (e.g. "refs/heads/main", "refs/heads/feature/new-feature")
            stages_to_skip (list): Stage names to skip (e.g. ["Security", "Performance"])
            resources (dict): Override repository branches/versions used by the pipeline
                            Example: {"repositories": {"external-repo": {"refName": "refs/heads/stable"}}}

        Returns:
            PipelineOutcome: Complete execution results including:
                - success: Boolean indicating if pipeline completed successfully
                - pipeline_run: Details about the pipeline run
                - execution_time: How long the pipeline took to complete
                - failure_summary: If failed, detailed analysis of what went wrong

        Examples:
            # Run a simple pipeline
            run_pipeline_and_get_outcome("MyProject", "CI Pipeline")

            # Run with variables
            run_pipeline_and_get_outcome(
                "MyProject",
                "Deploy Pipeline",
                variables={"environment": "staging"}
            )

            # Run with timeout and custom branch
            run_pipeline_and_get_outcome(
                "MyProject",
                "Integration Tests",
                timeout_seconds=600,
                branch="refs/heads/feature/new-feature"
            )
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None

        # Create request if any parameters are provided
        request = None
        if any([variables, template_parameters, branch, stages_to_skip, resources]):
            from .models import PipelineRunRequest

            request = PipelineRunRequest(
                variables=variables,
                templateParameters=template_parameters,
                branch=branch,
                stagesToSkip=stages_to_skip,
                resources=resources,
            )

        return ado_client_instance.run_pipeline_and_get_outcome_by_name(
            project_name, pipeline_name, request, timeout_seconds, max_lines
        )

    # 🔍 ENHANCED PROJECT DISCOVERY TOOLS

    @mcp_instance.tool
    def find_project_by_id_or_name(
        identifier: str, include_suggestions: bool = True
    ) -> Project | None:
        """
        Find a project by either ID or name with fuzzy matching support.

        This tool provides unified project discovery that accepts both project IDs (UUID format)
        and project names, with intelligent fuzzy matching and helpful error suggestions.

        Args:
            identifier (str): Project ID (UUID format) or project name to search for
            include_suggestions (bool): Whether to include fuzzy match suggestions on failure (default: True)

        Returns:
            Project: Project object if found, None if not found

        Examples:
            # Find by exact name
            find_project_by_id_or_name("MyProject")

            # Find by UUID
            find_project_by_id_or_name("12345678-1234-1234-1234-123456789abc")

            # Find with typos (fuzzy matching)
            find_project_by_id_or_name("MyProj")  # Might match "MyProject"
        """
        ado_client_instance, error_return = get_client_or_error()
        if ado_client_instance is None:
            return error_return

        try:
            enhanced_tools = EnhancedProjectTools(ado_client_instance)
            return enhanced_tools.find_project_by_id_or_name(identifier, include_suggestions)
        except Exception as e:
            logger.error(f"Error in find_project_by_id_or_name: {e}")
            return None

    @mcp_instance.tool
    def list_all_projects_with_metadata() -> list[dict[str, Any]]:
        """
        List all projects with enhanced metadata for better LLM understanding.

        Returns comprehensive project information including descriptions, URLs, states,
        and visibility settings to help LLMs make better decisions about project selection.

        Returns:
            List[dict]: List of project dictionaries with enhanced metadata including:
                - id: Project UUID
                - name: Project name
                - description: Project description
                - url: Project URL
                - state: Project state (e.g., wellFormed, createPending)
                - visibility: Project visibility (private, public, etc.)

        Examples:
            # Get all projects with full metadata
            projects = list_all_projects_with_metadata()
            for project in projects:
                print(f"{project['name']}: {project['description']}")
        """
        ado_client_instance, error_return = get_client_or_error([])
        if ado_client_instance is None:
            return error_return

        try:
            enhanced_tools = EnhancedProjectTools(ado_client_instance)
            return enhanced_tools.list_all_projects_with_metadata()
        except Exception as e:
            logger.error(f"Error in list_all_projects_with_metadata: {e}")
            return []

    @mcp_instance.tool
    def get_project_suggestions(
        query: str, max_suggestions: int = 10, max_tokens: int = 1000
    ) -> dict[str, Any]:
        """
        Get fuzzy match suggestions for a project query that didn't find exact matches.

        This tool is useful when a project lookup fails and you want to provide helpful
        suggestions to the user based on similar project names.

        Args:
            query (str): The project name query that failed to find exact matches
            max_suggestions (int): Maximum number of suggestions to return (default: 10)
            max_tokens (int): Maximum tokens allowed in response to prevent context overflow (default: 1000)

        Returns:
            dict: Dictionary containing:
                - query: The original search query
                - found: Boolean indicating if exact match was found (always False for this tool)
                - suggestions: List of similar projects with similarity scores
                - message: User-friendly error message with suggestions
                - total_matches: Total number of matches found before limiting
                - limited_by_tokens: Whether results were limited due to token constraints

        Examples:
            # Get suggestions for a typo
            suggestions = get_project_suggestions("MyProj")
            # Might return suggestions like "MyProject", "MyProjectTest", etc.

            # Limit suggestions
            suggestions = get_project_suggestions("Test", max_suggestions=5)
        """
        ado_client_instance, error_return = get_client_or_error({})
        if ado_client_instance is None:
            return error_return

        try:
            enhanced_tools = EnhancedProjectTools(ado_client_instance)
            return enhanced_tools.get_project_suggestions(query, max_suggestions, max_tokens)
        except Exception as e:
            logger.error(f"Error in get_project_suggestions: {e}")
            return {
                "query": query,
                "found": False,
                "suggestions": [],
                "message": f"Error getting suggestions for '{query}': {str(e)}",
                "error": True,
            }

    # 🚀 NAME-BASED TOOLS - USER-FRIENDLY INTERFACES

    @mcp_instance.tool
    def find_project_by_name(name: str) -> Project | None:
        """
        🔍 FIND PROJECT BY NAME: Find a project using its name with fuzzy matching.

        ⚡ USE THIS WHEN: User provides a project name instead of project ID

        This tool provides intelligent name matching:
        - Exact name matching first
        - Fuzzy matching for typos (e.g., "MyProj" matches "MyProject")
        - Case-insensitive search
        - Cached results for fast repeated lookups

        Perfect for: "Find the Learning project" or "Get info about my main project"

        Args:
            name (str): Project name to search for (fuzzy matching enabled)

        Returns:
            Project: Project object if found, None if not found
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None

        return ado_client_instance.find_project_by_name(name)

    @mcp_instance.tool
    def find_pipeline_by_name(project_name: str, pipeline_name: str) -> dict | None:
        """
        🔍 FIND PIPELINE BY NAME: Find a pipeline using project and pipeline names.

        ⚡ USE THIS WHEN: User provides names instead of IDs

        This tool provides intelligent name matching for both project and pipeline:
        - Fuzzy matching for both names
        - Automatic caching for fast lookups
        - Returns both project and pipeline info

        Perfect for: "Find the CI pipeline in Learning project"

        Args:
            project_name (str): Project name (fuzzy matching enabled)
            pipeline_name (str): Pipeline name (fuzzy matching enabled)

        Returns:
            dict: Contains project and pipeline info if found, None otherwise
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None

        result = ado_client_instance.find_pipeline_by_name(project_name, pipeline_name)
        if result:
            project, pipeline = result
            return {
                "project": project,
                "pipeline": pipeline,
                "project_id": project.id,
                "pipeline_id": pipeline.id,
            }
        return None

    @mcp_instance.tool
    def run_pipeline_by_name(
        project_name: str,
        pipeline_name: str,
        variables: dict[str, Any] | None = None,
        template_parameters: dict[str, Any] | None = None,
        branch: str | None = None,
        stages_to_skip: list[str] | None = None,
        resources: RunResourcesParameters | None = None,
    ) -> PipelineRun | None:
        """
        🚀 RUN PIPELINE BY NAME: Execute a pipeline using natural names.

        ⚡ USE THIS WHEN: User wants to run a pipeline but only knows names

        Much easier than finding IDs first! This tool:
        - Finds project and pipeline by name automatically
        - Handles fuzzy matching for typos
        - Uses intelligent caching for fast lookups
        - Starts the pipeline execution

        Perfect for: "Run the CI pipeline in Learning project"

        Args:
            project_name (str): Project name (fuzzy matching enabled)
            pipeline_name (str): Pipeline name (fuzzy matching enabled)
            variables (Dict[str, Union[str, Variable]]): Runtime variables to pass to the pipeline
                             ⚠️  IMPORTANT: Variables must be configured in Azure DevOps UI as "settable at queue time"
                             Variables defined in YAML cannot be overridden at queue time.
                             Accepts both simple strings and Variable objects:
                             - String format: {"myVar": "myValue"}
                             - Object format: {"myVar": {"value": "myValue", "isSecret": false}}
            template_parameters (dict): Template parameters for pipelines with parameters: block in YAML
                             More flexible than variables for conditional pipeline logic
                             Example: {"environment": "prod", "enableDebug": true}
            branch (str): Branch to run the pipeline from (e.g., "refs/heads/main" or "refs/heads/feature/my-branch")
            stages_to_skip (list): List of stage names to skip during execution
            resources (RunResourcesParameters): 🔧 DYNAMIC REPOSITORY RESOURCES - Override YAML-defined repository branches

                             IMPORTANT: Pass as a dictionary/object, NOT a JSON string!

                             ✅ CORRECT: {"repositories": {"tooling": {"refName": "refs/heads/stable/0.0.1"}}}
                             ❌ WRONG: '{"repositories": {"tooling": {"refName": "refs/heads/stable/0.0.1"}}}'

        Returns:
            PipelineRun: Pipeline run details if successful, None otherwise
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None

        # Create request if any parameters are provided
        request = None
        if any([variables, template_parameters, branch, stages_to_skip, resources]):
            from .models import PipelineRunRequest

            request = PipelineRunRequest(
                variables=variables,
                templateParameters=template_parameters,
                branch=branch,
                stagesToSkip=stages_to_skip,
                resources=resources,
            )

        return ado_client_instance.run_pipeline_by_name(project_name, pipeline_name, request)

    @mcp_instance.tool
    def get_pipeline_failure_summary_by_name(
        project_name: str, pipeline_name: str, run_id: int, max_lines: int = 100
    ) -> FailureSummary | None:
        """
        🔥 ANALYZE FAILURES BY NAME: Get failure analysis using natural names.

        ⚡ USE THIS WHEN: User wants to debug a failed pipeline using names

        This combines the power of failure analysis with name-based lookup:
        - Finds project and pipeline by name automatically
        - Provides comprehensive failure analysis
        - Includes log content for failing steps
        - Much easier than managing IDs

        Perfect for: "Why did the CI pipeline fail in Learning project?"

        Args:
            project_name (str): Project name (fuzzy matching enabled)
            pipeline_name (str): Pipeline name (fuzzy matching enabled)
            run_id (int): Pipeline run ID (from pipeline URL or previous run)
            max_lines (int): Maximum log lines to return (default: 100)

        Returns:
            FailureSummary: Detailed failure analysis if found, None otherwise
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None

        return ado_client_instance.get_pipeline_failure_summary_by_name(
            project_name, pipeline_name, run_id, max_lines
        )

    @mcp_instance.tool
    def run_pipeline_and_get_outcome_by_name(
        project_name: str,
        pipeline_name: str,
        timeout_seconds: int = 300,
        max_lines: int = 100,
        variables: dict[str, Any] | None = None,
        template_parameters: dict[str, Any] | None = None,
        branch: str | None = None,
        stages_to_skip: list[str] | None = None,
        resources: RunResourcesParameters | None = None,
    ) -> PipelineOutcome | None:
        """
        🚀 RUN & ANALYZE BY NAME: Execute pipeline by name and get complete results.

        ⚡ USE THIS WHEN: User wants to run a pipeline and see results using names

        The ultimate user-friendly pipeline execution tool:
        - Finds project and pipeline by name automatically
        - Starts pipeline execution
        - Waits for completion (up to timeout)
        - Returns success/failure with detailed analysis
        - Includes failure logs if it fails

        Perfect for: "Run the CI pipeline in Learning and tell me what happens"

        Args:
            project_name (str): Project name (fuzzy matching enabled)
            pipeline_name (str): Pipeline name (fuzzy matching enabled)
            timeout_seconds (int): Max wait time (default: 300s = 5 minutes)
            max_lines (int): Maximum log lines to return (default: 100)
            variables (Dict[str, Union[str, Variable]]): Runtime variables to pass to the pipeline
                             ⚠️  IMPORTANT: Variables must be configured in Azure DevOps UI as "settable at queue time"
                             Variables defined in YAML cannot be overridden at queue time.
                             Accepts both simple strings and Variable objects:
                             - String format: {"myVar": "myValue"}
                             - Object format: {"myVar": {"value": "myValue", "isSecret": false}}
            template_parameters (dict): Template parameters for pipelines with parameters: block in YAML
                             More flexible than variables for conditional pipeline logic
                             Example: {"environment": "prod", "enableDebug": true}
            branch (str): Branch to run the pipeline from (e.g., "refs/heads/main" or "refs/heads/feature/my-branch")
            stages_to_skip (list): List of stage names to skip during execution
            resources (RunResourcesParameters): 🔧 DYNAMIC REPOSITORY RESOURCES - Override YAML-defined repository branches

                             IMPORTANT: Pass as a dictionary/object, NOT a JSON string!

                             ✅ CORRECT: {"repositories": {"tooling": {"refName": "refs/heads/stable/0.0.1"}}}
                             ❌ WRONG: '{"repositories": {"tooling": {"refName": "refs/heads/stable/0.0.1"}}}'

        Returns:
            PipelineOutcome: Complete execution results, None if not found
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None

        # Create request if any parameters are provided
        request = None
        if any([variables, template_parameters, branch, stages_to_skip, resources]):
            from .models import PipelineRunRequest

            request = PipelineRunRequest(
                variables=variables,
                templateParameters=template_parameters,
                branch=branch,
                stagesToSkip=stages_to_skip,
                resources=resources,
            )

        return ado_client_instance.run_pipeline_and_get_outcome_by_name(
            project_name, pipeline_name, request, timeout_seconds, max_lines
        )

    @mcp_instance.tool
    def list_available_projects() -> list[str]:
        """
        📋 LIST PROJECT NAMES: Get all available project names for easy reference.

        ⚡ USE THIS WHEN: User wants to see what projects are available

        Returns a simple list of project names that can be used with other name-based tools.
        Uses intelligent caching so repeated calls are fast.

        Perfect for: "What projects are available?" or "Show me all projects"

        Returns:
            List[str]: List of project names available in the organization
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return []

        return ado_client_instance.list_available_projects()

    @mcp_instance.tool
    def list_available_pipelines(project_name: str) -> list[str]:
        """
        📋 LIST PIPELINE NAMES: Get all pipeline names for a project.

        ⚡ USE THIS WHEN: User wants to see what pipelines are available in a project

        Returns a simple list of pipeline names for the specified project.
        Uses intelligent caching and name matching for the project.

        Perfect for: "What pipelines are in Learning project?"

        Args:
            project_name (str): Project name (fuzzy matching enabled)

        Returns:
            List[str]: List of pipeline names in the project, empty list if project not found
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return []

        return ado_client_instance.list_available_pipelines(project_name)

    # Register work item tools
    register_work_item_tools(mcp_instance, client_container)

    # Register process and template tools
    from ado.processes.tools import register_process_tools

    register_process_tools(mcp_instance, client_container)
