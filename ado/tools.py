import logging
import os
from typing import Any, Dict, List, Optional, Union, Union

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
    RepositoryResourceParameters,
    ServiceConnection,
    StepFailure,
    TimelineResponse,
    Variable,
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
    def list_projects() -> List[Project]:
        """
        Lists all projects in the Azure DevOps organization.

        Returns:
            List[Project]: A list of Project objects.
        """
        ado_client_instance = client_container.get("client")
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
    def run_pipeline(
        project_id: str,
        pipeline_id: int,
        variables: Optional[Dict[str, Any]] = None,
        template_parameters: Optional[Dict[str, Any]] = None,
        branch: Optional[str] = None,
        stages_to_skip: Optional[List[str]] = None,
        resources: Optional[RunResourcesParameters] = None,
    ) -> Optional[PipelineRun]:
        """
        Triggers a run for a specific pipeline in an Azure DevOps project.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.
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
                             
                             IMPORTANT: Use proper Azure DevOps API schema structure!
                             
                             📋 YAML Example:
                             resources:
                               repositories:
                                 - repository: tooling
                                   type: github
                                   name: raboley/tooling
                                   ref: refs/heads/main
                             
                             📋 MCP Command Example (proper schema):
                             resources: {
                               "repositories": {
                                 "tooling": {
                                   "refName": "refs/heads/stable/0.0.1"
                                 }
                               }
                             }
                             
                             Available resource types:
                             - repositories: {"repoName": {"refName": "refs/heads/branch", "version": "commit-hash"}}
                             - builds: {"buildName": {"version": "build-version"}}
                             - containers: {"containerName": {"version": "tag"}}
                             - packages: {"packageName": {"version": "package-version"}}
                             - pipelines: {"pipelineName": {"version": "pipeline-version"}}
                             
                             Common use cases:
                             - Override external repo branch: {"repositories": {"tooling": {"refName": "refs/heads/stable/0.0.1"}}}
                             - Override self repo branch: {"repositories": {"self": {"refName": "refs/heads/feature/my-branch"}}}
                             - Override multiple repos: {"repositories": {"tooling": {"refName": "refs/heads/v1.0"}, "self": {"refName": "refs/heads/main"}}}

        Returns:
            Optional[PipelineRun]: A PipelineRun object representing the pipeline run details, or None if client unavailable.
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
                resources=resources
            )
        
        return ado_client_instance.run_pipeline(project_id, pipeline_id, request)

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
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None
        return ado_client_instance.get_pipeline_run(project_id, pipeline_id, run_id)

    def _inject_github_tokens_if_needed(ado_client_instance, project_id: str, pipeline_id: int, resources_dict: Optional[dict]) -> Optional[dict]:
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
                logger.debug(f"Repository '{repo_name}' has no RepositoryType specified, assuming public repository")
                continue
                
            if repo_type == "gitHub":
                # Only inject if token is not already provided
                if "token" not in repo_params:
                    repo_params["token"] = github_token
                    repo_params["tokenType"] = "Basic"
                    logger.info(f"Injected GitHub token for private repository '{repo_name}' (RepositoryType: gitHub)")
                else:
                    logger.debug(f"Repository '{repo_name}' already has token provided, skipping injection")
            else:
                logger.warning(f"Repository '{repo_name}' has unsupported RepositoryType: '{repo_type}'. Currently only 'gitHub' is supported for automatic token injection.")
            
        return resources_dict

    @mcp_instance.tool
    def preview_pipeline(
        project_id: str,
        pipeline_id: int,
        yaml_override: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
        template_parameters: Optional[Dict[str, Any]] = None,
        stages_to_skip: Optional[List[str]] = None,
        resources: Optional[RunResourcesParameters] = None,
    ) -> Optional[PreviewRun]:
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
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.
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

        # Build the preview request - convert resources to dict if provided
        resources_dict = None
        if resources:
            resources_dict = resources.dict(exclude_none=True) if hasattr(resources, 'dict') else resources
            
            # Auto-inject GitHub tokens for GitHub repositories only
            resources_dict = _inject_github_tokens_if_needed(ado_client_instance, project_id, pipeline_id, resources_dict)
        
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
        project_id: str, pipeline_id: int, run_id: int, max_lines: int = 100
    ) -> Optional[FailureSummary]:
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
        step_name: Optional[str] = None,
        max_lines: int = 100,
    ) -> Optional[List[StepFailure]]:
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
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None

        return ado_client_instance.get_pipeline_timeline(project_id, pipeline_id, run_id)

    @mcp_instance.tool
    def list_pipeline_logs(project_id: str, pipeline_id: int, run_id: int) -> Optional[LogCollection]:
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
    ) -> Optional[str]:
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
        project_id: str,
        pipeline_id: int,
        timeout_seconds: int = 300,
        max_lines: int = 100,
        variables: Optional[Dict[str, Any]] = None,
        template_parameters: Optional[Dict[str, Any]] = None,
        branch: Optional[str] = None,
        stages_to_skip: Optional[List[str]] = None,
        resources: Optional[RunResourcesParameters] = None,
    ) -> Optional[PipelineOutcome]:
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
                             
                             📋 YAML Example:
                             resources:
                               repositories:
                                 - repository: tooling
                                   type: github
                                   name: raboley/tooling
                                   ref: refs/heads/main
                             
                             📋 MCP Command Example:
                             resources: {
                               "repositories": {
                                 "tooling": {
                                   "refName": "refs/heads/stable/0.0.1"
                                 }
                               }
                             }
                             
                             ✅ CORRECT: Pass dictionary object
                             ❌ WRONG: Pass JSON string like '{"repositories": ...}'
                             
                             Common use cases:
                             - Override external repo branch: {"repositories": {"tooling": {"refName": "refs/heads/stable/0.0.1"}}}
                             - Override self repo branch: {"repositories": {"self": {"refName": "refs/heads/feature/my-branch"}}}

        Returns:
            PipelineOutcome: Complete results with pipeline_run, success flag, failure_summary, execution_time
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
                resources=resources
            )

        return ado_client_instance.run_pipeline_and_get_outcome(
            project_id, pipeline_id, request, timeout_seconds, max_lines
        )

    # 🚀 NAME-BASED TOOLS - USER-FRIENDLY INTERFACES
    
    @mcp_instance.tool
    def find_project_by_name(name: str) -> Optional[Project]:
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
    def find_pipeline_by_name(project_name: str, pipeline_name: str) -> Optional[Dict]:
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
                "pipeline_id": pipeline.id
            }
        return None
    
    @mcp_instance.tool
    def run_pipeline_by_name(
        project_name: str,
        pipeline_name: str,
        variables: Optional[Dict[str, Any]] = None,
        template_parameters: Optional[Dict[str, Any]] = None,
        branch: Optional[str] = None,
        stages_to_skip: Optional[List[str]] = None,
        resources: Optional[RunResourcesParameters] = None,
    ) -> Optional[PipelineRun]:
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
                resources=resources
            )
        
        return ado_client_instance.run_pipeline_by_name(project_name, pipeline_name, request)
    
    @mcp_instance.tool
    def get_pipeline_failure_summary_by_name(
        project_name: str, pipeline_name: str, run_id: int, max_lines: int = 100
    ) -> Optional[FailureSummary]:
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
        variables: Optional[Dict[str, Any]] = None,
        template_parameters: Optional[Dict[str, Any]] = None,
        branch: Optional[str] = None,
        stages_to_skip: Optional[List[str]] = None,
        resources: Optional[RunResourcesParameters] = None,
    ) -> Optional[PipelineOutcome]:
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
                resources=resources
            )
        
        return ado_client_instance.run_pipeline_and_get_outcome_by_name(
            project_name, pipeline_name, request, timeout_seconds, max_lines
        )
    
    @mcp_instance.tool
    def list_available_projects() -> List[str]:
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
    def list_available_pipelines(project_name: str) -> List[str]:
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
