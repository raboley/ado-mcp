"""Pipeline logging and failure analysis operations."""

import logging

import requests

from ..models import (
    FailureSummary,
    LogCollection,
    StepFailure,
    TimelineResponse,
)

logger = logging.getLogger(__name__)


class LogOperations:
    """Azure DevOps pipeline logging and failure analysis operations."""

    def __init__(self, client_core):
        """Initialize with reference to core client."""
        self._client = client_core

    def list_pipeline_logs(self, project_id: str, pipeline_id: int, run_id: int) -> LogCollection:
        """
        List logs for a specific pipeline run.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.
            run_id (int): The ID of the pipeline run.

        Returns:
            LogCollection: A collection of log entries for the pipeline run.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
        """
        url = f"{self._client.organization_url}/{project_id}/_apis/pipelines/{pipeline_id}/runs/{run_id}/logs?api-version=7.2-preview.1"
        logger.info(f"Listing logs for pipeline run {run_id} in project {project_id}")
        response = self._client._send_request("GET", url)
        logger.info(f"Retrieved {len(response.get('logs', []))} logs for run {run_id}")
        return LogCollection(**response)

    def get_log_content_by_id(
        self, project_id: str, pipeline_id: int, run_id: int, log_id: int, max_lines: int = 100
    ) -> str:
        """
        Get the content of a specific log from a pipeline run.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.
            run_id (int): The ID of the pipeline run.
            log_id (int): The ID of the specific log.
            max_lines (int): Maximum number of lines to return from the end of the log (default: 100).
                           Set to 0 or negative to return all lines.

        Returns:
            str: The log content as a string, limited to the last max_lines.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
        """
        # Get log metadata with signed content URL
        url = f"{self._client.organization_url}/{project_id}/_apis/pipelines/{pipeline_id}/runs/{run_id}/logs/{log_id}?$expand=signedContent&api-version=7.2-preview.1"
        logger.info(f"Getting log content for log {log_id} from run {run_id}")
        response = self._client._send_request("GET", url)

        # Extract and fetch content from signed URL
        if "signedContent" in response and "url" in response["signedContent"]:
            signed_url = response["signedContent"]["url"]
            content_response = requests.get(signed_url)
            content_response.raise_for_status()

            full_content = content_response.text

            # Apply line limiting if max_lines is positive
            if max_lines > 0:
                lines = full_content.splitlines()
                if len(lines) > max_lines:
                    limited_lines = lines[-max_lines:]  # Get last max_lines
                    limited_content = "\n".join(limited_lines)
                    logger.info(
                        f"Retrieved log content for log {log_id}: {len(lines)} total lines, "
                        f"showing last {max_lines} lines ({len(limited_content)} characters)"
                    )
                    return limited_content
                else:
                    logger.info(
                        f"Retrieved log content for log {log_id}: {len(lines)} lines "
                        f"({len(full_content)} characters) - under limit"
                    )
                    return full_content
            else:
                logger.info(
                    f"Retrieved full log content for log {log_id} ({len(full_content)} characters)"
                )
                return full_content

        logger.warning(f"No signed content URL found for log {log_id}")
        return ""

    def get_pipeline_timeline(
        self, project_id: str, pipeline_id: int, run_id: int
    ) -> TimelineResponse:
        """
        Get the build timeline for a pipeline run, showing status of all stages, jobs, and tasks.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.
            run_id (int): The ID of the pipeline run (also serves as build ID).

        Returns:
            TimelineResponse: The timeline showing status of all pipeline components.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
        """
        # Use the run_id as build_id for the build timeline API
        url = f"{self._client.organization_url}/{project_id}/_apis/build/builds/{run_id}/timeline?api-version=7.2-preview.2"
        logger.info(f"Getting timeline for pipeline run {run_id} in project {project_id}")
        response = self._client._send_request("GET", url)
        logger.info(
            f"Retrieved timeline with {len(response.get('records', []))} records for run {run_id}"
        )
        return TimelineResponse(**response)

    def get_pipeline_failure_summary(
        self, project_id: str, pipeline_id: int, run_id: int, max_lines: int = 100
    ) -> FailureSummary:
        """
        Get a comprehensive summary of pipeline failures, including root causes and affected components.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.
            run_id (int): The ID of the pipeline run.
            max_lines (int): Maximum number of lines to return from the end of each log (default: 100).
                           Set to 0 or negative to return all lines.

        Returns:
            FailureSummary: Detailed summary of failures with log content for root causes.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
        """
        # Import here to avoid circular imports
        from .builds import BuildOperations

        builds_ops = BuildOperations(self._client)

        logger.info(f"Analyzing failures for pipeline run {run_id}")

        # Get the timeline to identify failed steps
        timeline = self.get_pipeline_timeline(project_id, pipeline_id, run_id)

        # Find all failed records
        failed_records = [record for record in timeline.records if record.result == "failed"]

        # Separate root causes (Tasks) from hierarchy failures (Jobs, Stages)
        root_cause_tasks = []
        hierarchy_failures = []

        for record in failed_records:
            # Extract issues as strings
            issues = []
            if record.issues:
                issues = [issue.get("message", "Unknown error") for issue in record.issues]

            step_failure = StepFailure(
                step_name=record.name or "Unknown Step",
                step_type=record.type or "Unknown",
                result=record.result or "failed",
                log_id=record.log.get("id") if record.log else None,
                issues=issues,
                start_time=record.startTime,
                finish_time=record.finishTime,
            )

            # Get log content for tasks with logs
            if record.type == "Task" and step_failure.log_id:
                try:
                    step_failure.log_content = self.get_log_content_by_id(
                        project_id, pipeline_id, run_id, step_failure.log_id, max_lines
                    )
                except Exception as e:
                    logger.warning(f"Failed to get log content for step {record.name}: {e}")
                    step_failure.log_content = f"Error retrieving log: {e}"

            # Categorize failures
            if record.type == "Task":
                root_cause_tasks.append(step_failure)
            else:
                hierarchy_failures.append(step_failure)

        # Get pipeline URL from the run
        pipeline_run = builds_ops.get_pipeline_run(project_id, pipeline_id, run_id)
        pipeline_url = None
        if hasattr(pipeline_run, "_links") and pipeline_run._links:
            pipeline_url = pipeline_run._links.get("web", {}).get("href")

        total_failed = len(failed_records)
        logger.info(
            f"Found {total_failed} failed steps: {len(root_cause_tasks)} root causes, {len(hierarchy_failures)} hierarchy failures"
        )

        return FailureSummary(
            total_failed_steps=total_failed,
            root_cause_tasks=root_cause_tasks,
            hierarchy_failures=hierarchy_failures,
            pipeline_url=pipeline_url,
            build_id=run_id,
        )

    def get_failed_step_logs(
        self,
        project_id: str,
        pipeline_id: int,
        run_id: int,
        step_name: str | None = None,
        max_lines: int = 100,
    ) -> list[StepFailure]:
        """
        Get detailed log information for failed steps, optionally filtered by step name.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.
            run_id (int): The ID of the pipeline run.
            step_name (Optional[str]): Filter to specific step name (case-insensitive partial match).
            max_lines (int): Maximum number of lines to return from the end of each log (default: 100).
                           Set to 0 or negative to return all lines.

        Returns:
            List[StepFailure]: List of failed steps with their log content.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
        """
        logger.info(
            f"Getting failed step logs for run {run_id}"
            + (f" filtered by '{step_name}'" if step_name else "")
        )

        # Get the failure summary which already has logs
        failure_summary = self.get_pipeline_failure_summary(
            project_id, pipeline_id, run_id, max_lines
        )

        # Combine root cause tasks and hierarchy failures
        all_failures = failure_summary.root_cause_tasks + failure_summary.hierarchy_failures

        # Filter by step name if provided
        if step_name:
            step_name_lower = step_name.lower()
            filtered_failures = []
            for failure in all_failures:
                if step_name_lower in failure.step_name.lower():
                    filtered_failures.append(failure)
            logger.info(f"Filtered to {len(filtered_failures)} steps matching '{step_name}'")
            return filtered_failures

        logger.info(f"Returning {len(all_failures)} failed steps")
        return all_failures
