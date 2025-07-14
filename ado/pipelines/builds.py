"""Pipeline build and run operations."""

import logging
import time
from typing import Any

from ..models import PipelineOutcome, PipelineRun

logger = logging.getLogger(__name__)


class BuildOperations:
    """Azure DevOps pipeline build and run operations."""

    def __init__(self, client_core):
        """Initialize with reference to core client."""
        self._client = client_core

    def run_pipeline(self, project_id: str, pipeline_id: int) -> PipelineRun:
        """
        Trigger a run for a specific pipeline.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.

        Returns:
            PipelineRun: A PipelineRun object representing the pipeline run details.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
        """
        url = f"{self._client.organization_url}/{project_id}/_apis/pipelines/{pipeline_id}/runs?api-version=7.2-preview.1"
        logger.info(f"Running pipeline {pipeline_id} in project {project_id}")
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
        url = f"{self._client.organization_url}/{project_id}/_apis/pipelines/{pipeline_id}/runs/{run_id}?api-version=7.2-preview.1"
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

    def run_pipeline_and_get_outcome(
        self, project_id: str, pipeline_id: int, timeout_seconds: int = 300, max_lines: int = 100
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
        pipeline_run = self.run_pipeline(project_id, pipeline_id)
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
