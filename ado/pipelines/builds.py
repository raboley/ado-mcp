"""Pipeline build and run operations."""

import logging
import time
from typing import Any

from ..models import PipelineOutcome, PipelineRun, PipelineRunRequest

logger = logging.getLogger(__name__)


class BuildOperations:
    """Azure DevOps pipeline build and run operations."""

    def __init__(self, client_core):
        """Initialize with reference to core client."""
        self._client = client_core

    def run_pipeline(
        self, project_id: str, pipeline_id: int, request: PipelineRunRequest | None = None
    ) -> PipelineRun:
        """
        Trigger a run for a specific pipeline.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.
            request (Optional[PipelineRunRequest]): Optional request with variables, parameters, and branch.

        Returns:
            PipelineRun: A PipelineRun object representing the pipeline run details.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
            ValueError: If the pipeline doesn't support the requested resources or branch override.
        """
        url = f"{self._client.organization_url}/{project_id}/_apis/pipelines/{pipeline_id}/runs?api-version=7.1"

        # Validate if branch/self repository resources are supported before sending the request
        # Note: Only validate for 'self' repository overrides and branch parameters
        # External repository overrides (like 'tooling', 'templates', etc.) typically work
        has_self_repo_override = (
            request
            and request.resources
            and request.resources.repositories
            and "self" in request.resources.repositories
        )

        if request and (request.branch or has_self_repo_override):
            try:
                self._validate_pipeline_supports_resources(project_id, pipeline_id, request)
            except ValueError as e:
                # Re-raise validation errors to prevent bad requests
                logger.error(f"Resource validation failed: {e}")
                raise
            except Exception as e:
                logger.warning(f"Resource validation failed, proceeding anyway: {e}")
                # Continue execution for other types of errors (network, auth, etc.)

        # Prepare request data
        request_data = {}
        if request:
            request_dict = request.model_dump(exclude_none=True)

            # Handle variables: convert Union[str, Variable] to proper Azure DevOps format
            if "variables" in request_dict and request_dict["variables"]:
                processed_variables = {}
                for key, value in request_dict["variables"].items():
                    if isinstance(value, str):
                        # Convert string to Variable object format for Azure DevOps API
                        processed_variables[key] = {"value": value}
                    elif isinstance(value, dict) and "value" in value:
                        # Already in Variable object format
                        processed_variables[key] = value
                    else:
                        # Fallback: treat as string value
                        processed_variables[key] = {"value": str(value)}
                request_dict["variables"] = processed_variables

            # Handle resources and branch - branch needs to be merged into resources.repositories.self.refName
            resources = request_dict.get("resources", {})
            if request.branch:
                # Branch override is only supported for pipelines that use repositories
                # Adding 'self' repository override for branch specification
                logger.info(f"Adding branch override: {request.branch}")
                # Ensure repositories exists
                if "repositories" not in resources:
                    resources["repositories"] = {}
                # Set the self repository branch (for when running from a different branch)
                resources["repositories"]["self"] = {"refName": request.branch}
                # Remove branch from the dict as we've handled it
                request_dict.pop("branch", None)

            # Set resources in request_data if they exist (either from original request or from branch handling)
            if resources:
                request_data["resources"] = resources
                # Remove resources from request_dict to avoid overwrite in update()
                request_dict.pop("resources", None)

            # Add other fields
            request_data.update(request_dict)

        logger.info(f"Running pipeline {pipeline_id} in project {project_id}")
        if request_data:
            logger.debug(f"Pipeline run request data: {request_data}")
            response = self._client._send_request("POST", url, json=request_data)
        else:
            # For basic pipeline runs without parameters, send empty JSON object
            # Azure DevOps requires a Content-Length header and expects JSON body
            logger.debug("Sending empty JSON body for basic pipeline run")
            response = self._client._send_request("POST", url, json={})
        logger.info(
            f"Pipeline run started: {response.get('id')} with state: {response.get('state')}"
        )
        return PipelineRun(**response)

    def get_pipeline_run(self, project_id: str, pipeline_id: int, run_id: int) -> PipelineRun:
        """
        Retrieve details for a specific pipeline run.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.
            run_id (int): The ID of the pipeline run.

        Returns:
            PipelineRun: A PipelineRun object representing the pipeline run details.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
        """
        url = f"{self._client.organization_url}/{project_id}/_apis/pipelines/{pipeline_id}/runs/{run_id}?api-version=7.1"
        logger.debug(f"Getting pipeline run {run_id} details for project {project_id}")
        response = self._client._send_request("GET", url)
        logger.debug(
            f"Pipeline run {run_id} state: {response.get('state')}, result: {response.get('result')}"
        )
        return PipelineRun(**response)

    def get_build_by_id(self, project_id: str, build_id: int) -> dict[str, Any]:
        """
        Retrieve build details by build ID using the Azure DevOps Build API.

        This method uses the Build API to get comprehensive build information,
        including the definition (pipeline) details from just the build/run ID.

        Args:
            project_id (str): The ID of the project.
            build_id (int): The ID of the build/run.

        Returns:
            dict: Build details including definition information.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
        """
        url = f"{self._client.organization_url}/{project_id}/_apis/build/builds/{build_id}?api-version=7.1"
        logger.info(f"Getting build details for build {build_id} in project {project_id}")
        response = self._client._send_request("GET", url)
        logger.debug(f"Build {build_id} definition: {response.get('definition', {}).get('name')}")
        return response

    def wait_for_pipeline_completion(
        self,
        project_id: str,
        pipeline_id: int,
        run_id: int,
        timeout_seconds: int = 300,
        poll_interval_seconds: int = 10,
    ) -> PipelineRun:
        """
        Wait for a pipeline run to complete by polling its status.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.
            run_id (int): The ID of the pipeline run.
            timeout_seconds (int): Maximum time to wait in seconds. Defaults to 300 (5 minutes).
            poll_interval_seconds (int): Time between status checks in seconds. Defaults to 10.

        Returns:
            PipelineRun: The final pipeline run object.

        Raises:
            TimeoutError: If the pipeline doesn't complete within the timeout period.
            requests.exceptions.RequestException: For network-related errors.
        """
        start_time = time.time()
        logger.info(f"Waiting for pipeline run {run_id} to complete (timeout: {timeout_seconds}s)")

        while True:
            # Check if we've exceeded the timeout
            elapsed_time = time.time() - start_time
            if elapsed_time > timeout_seconds:
                raise TimeoutError(
                    f"Pipeline run {run_id} did not complete within {timeout_seconds} seconds"
                )

            # Get the current status
            pipeline_run = self.get_pipeline_run(project_id, pipeline_id, run_id)

            # Check if the run has completed
            if pipeline_run.is_completed():
                logger.info(f"Pipeline run {run_id} completed with result: {pipeline_run.result}")
                return pipeline_run

            # Log current status and wait before next check
            logger.debug(f"Pipeline run {run_id} still in progress (state: {pipeline_run.state})")
            time.sleep(poll_interval_seconds)

    def watch_pipeline(
        self,
        project_id: str,
        pipeline_id: int,
        run_id: int,
        timeout_seconds: int = 300,
        max_lines: int = 100,
    ) -> PipelineOutcome:
        """
        Watch an already running pipeline and return the outcome with failure details if applicable.

        This method monitors an existing pipeline run:
        1. Waits for the pipeline to complete (or timeout)
        2. If the pipeline failed, gets failure analysis with logs

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.
            run_id (int): The ID of the already running pipeline.
            timeout_seconds (int): Maximum time to wait for completion (default: 300).
            max_lines (int): Maximum number of lines to return from the end of each log (default: 100).
                           Set to 0 or negative to return all lines.

        Returns:
            PipelineOutcome: Complete outcome including run details and failure summary if failed.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
            TimeoutError: If the pipeline doesn't complete within the timeout period.
        """
        # Import here to avoid circular imports
        from ..pipelines.logs import LogOperations

        logs_ops = LogOperations(self._client)

        start_time = time.time()
        logger.info(f"Watching pipeline run {run_id} for completion...")

        # Step 1: Get the initial status to ensure the run exists
        initial_run = self.get_pipeline_run(project_id, pipeline_id, run_id)

        if initial_run.is_completed():
            logger.info(
                f"Pipeline run {run_id} is already completed with result: {initial_run.result}"
            )
            final_run = initial_run
        else:
            # Step 2: Wait for completion
            try:
                final_run = self.wait_for_pipeline_completion(
                    project_id, pipeline_id, run_id, timeout_seconds
                )
            except TimeoutError:
                # Get the current status for the timeout response
                final_run = self.get_pipeline_run(project_id, pipeline_id, run_id)
                logger.warning(f"Pipeline run {run_id} timed out after {timeout_seconds} seconds")

        # Step 3: Calculate execution time
        execution_time = time.time() - start_time

        # Step 4: Determine success and get failure details if needed
        success = final_run.result == "succeeded" if final_run.result else False
        failure_summary = None

        if not success and final_run.is_completed():
            try:
                failure_summary = logs_ops.get_pipeline_failure_summary(
                    project_id, pipeline_id, run_id, max_lines
                )
                logger.info(f"Retrieved failure summary for failed pipeline run {run_id}")
            except Exception as e:
                logger.warning(f"Could not retrieve failure summary: {e}")

        # Step 5: Create and return the outcome
        outcome = PipelineOutcome(
            pipeline_run=final_run,
            success=success,
            failure_summary=failure_summary,
            execution_time_seconds=execution_time,
        )

        logger.info(
            f"Pipeline watch for run {run_id} completed in {execution_time:.2f}s with result: {final_run.result}"
        )
        return outcome

    def run_pipeline_and_get_outcome(
        self,
        project_id: str,
        pipeline_id: int,
        request: PipelineRunRequest | None = None,
        timeout_seconds: int = 300,
        max_lines: int = 100,
    ) -> PipelineOutcome:
        """
        Run a pipeline, wait for completion, and return the outcome with failure details if applicable.

        This method combines multiple operations:
        1. Triggers the pipeline run
        2. Waits for the pipeline to complete (or timeout)
        3. If the pipeline failed, gets failure analysis with logs

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.
            request (Optional[PipelineRunRequest]): Optional request with variables, parameters, and branch.
            timeout_seconds (int): Maximum time to wait for completion (default: 300).
            max_lines (int): Maximum number of lines to return from the end of each log (default: 100).
                           Set to 0 or negative to return all lines.

        Returns:
            PipelineOutcome: Complete outcome including run details and failure summary if failed.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
            TimeoutError: If the pipeline doesn't complete within the timeout period.
        """
        # Import here to avoid circular imports
        from ..pipelines.logs import LogOperations

        logs_ops = LogOperations(self._client)

        start_time = time.time()
        logger.info(f"Starting pipeline {pipeline_id} and waiting for outcome...")

        # Step 1: Start the pipeline
        pipeline_run = self.run_pipeline(project_id, pipeline_id, request)
        run_id = pipeline_run.id

        # Step 2: Wait for completion
        try:
            final_run = self.wait_for_pipeline_completion(
                project_id, pipeline_id, run_id, timeout_seconds
            )
        except TimeoutError:
            # Get the current status for the timeout response
            final_run = self.get_pipeline_run(project_id, pipeline_id, run_id)
            logger.warning(f"Pipeline run {run_id} timed out after {timeout_seconds} seconds")

        # Step 3: Calculate execution time
        execution_time = time.time() - start_time

        # Step 4: Determine success and get failure details if needed
        success = final_run.result == "succeeded" if final_run.result else False
        failure_summary = None

        if not success and final_run.is_completed():
            try:
                failure_summary = logs_ops.get_pipeline_failure_summary(
                    project_id, pipeline_id, run_id, max_lines
                )
                logger.info(f"Retrieved failure summary for failed pipeline run {run_id}")
            except Exception as e:
                logger.warning(f"Could not retrieve failure summary: {e}")

        # Step 5: Create and return the outcome
        outcome = PipelineOutcome(
            pipeline_run=final_run,
            success=success,
            failure_summary=failure_summary,
            execution_time_seconds=execution_time,
        )

        logger.info(
            f"Pipeline {pipeline_id} completed in {execution_time:.2f}s with result: {final_run.result}"
        )
        return outcome

    def _validate_pipeline_supports_resources(
        self, project_id: str, pipeline_id: int, request: PipelineRunRequest
    ) -> None:
        """
        Validate if a pipeline supports the requested resources/branch by using pipeline preview.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.
            request (PipelineRunRequest): The pipeline run request to validate.

        Raises:
            ValueError: If the pipeline doesn't support the requested resources.
        """
        from ..models import PipelinePreviewRequest
        from ..pipelines.pipelines import PipelineOperations

        try:
            # Create a preview request to test if the pipeline supports resources
            preview_request = PipelinePreviewRequest(
                previewRun=True,
                resources=request.resources if request.resources else None,
            )

            # Add branch as a resource if specified
            if request.branch:
                if not preview_request.resources:
                    from ..models import RunResourcesParameters

                    preview_request.resources = RunResourcesParameters()
                if not preview_request.resources.repositories:
                    preview_request.resources.repositories = {}
                preview_request.resources.repositories["self"] = {"refName": request.branch}

            pipeline_ops = PipelineOperations(self._client)
            pipeline_ops.preview_pipeline(project_id, pipeline_id, preview_request)

            logger.info(f"Pipeline preview successful for pipeline {pipeline_id}")

        except Exception as e:
            error_msg = str(e).lower()
            if "400" in error_msg or "bad request" in error_msg:
                logger.error(
                    f"Pipeline {pipeline_id} does not support self repository branch overrides. "
                    f"This typically occurs with server-pool pipelines or pipelines without resources sections. "
                    f"External repository overrides may still work. Error: {e}"
                )
                raise ValueError(
                    f"Pipeline {pipeline_id} does not support branch overrides or 'self' repository resources. "
                    f"External repository overrides (like 'tooling', 'templates') may still work. "
                    f"For branch overrides, ensure the pipeline YAML includes a 'resources' section and uses a VM-based pool."
                ) from e
            else:
                # Re-raise other errors as they might be network or permission issues
                raise

    def extract_pipeline_run_data(self, project_id: str, pipeline_id: int, run_id: int) -> dict:
        """
        Extract resources, variables, and parameters from a pipeline run.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.
            run_id (int): The ID of the pipeline run.

        Returns:
            dict: Extracted data including repositories, variables, and parameters.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
        """
        from ..models import PipelineRunExtractionData, RepositoryInfo, VariableInfo

        logger.info(f"Extracting data from pipeline run {run_id}")

        # Get the pipeline run details
        pipeline_run = self.get_pipeline_run(project_id, pipeline_id, run_id)

        # Extract repositories from resources
        repositories = []
        if pipeline_run.resources and "repositories" in pipeline_run.resources:
            for repo_name, repo_data in pipeline_run.resources["repositories"].items():
                repo_info = RepositoryInfo(
                    name=repo_name,
                    full_name=repo_data.get("repository", {}).get("fullName"),
                    type=repo_data.get("repository", {}).get("type"),
                    ref_name=repo_data.get("refName"),
                    version=repo_data.get("version"),
                    connection_id=repo_data.get("repository", {}).get("connection", {}).get("id"),
                )
                repositories.append(repo_info)

        # Extract variables
        variables = []
        if pipeline_run.variables:
            for var_name, var_data in pipeline_run.variables.items():
                if isinstance(var_data, dict):
                    # Azure DevOps format: {"value": "...", "isSecret": false}
                    variable_info = VariableInfo(
                        name=var_name,
                        value=var_data.get("value"),
                        is_secret=var_data.get("isSecret", False),
                    )
                else:
                    # Simple string format
                    variable_info = VariableInfo(
                        name=var_name, value=str(var_data), is_secret=False
                    )
                variables.append(variable_info)

        # Note: Template parameters are not visible in pipeline run details
        # They would need to be extracted from the original run request or pipeline YAML
        template_parameters = {}

        # Note: Stages to skip are not preserved in run details
        stages_to_skip = []

        extraction_data = PipelineRunExtractionData(
            run_id=run_id,
            pipeline_name=pipeline_run.pipeline.name if pipeline_run.pipeline else None,
            repositories=repositories,
            variables=variables,
            template_parameters=template_parameters,
            stages_to_skip=stages_to_skip,
        )

        logger.info(
            f"Extracted {len(repositories)} repositories and {len(variables)} variables from run {run_id}"
        )
        return extraction_data.model_dump()
