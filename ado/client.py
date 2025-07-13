import os
import requests
from base64 import b64encode
import logging
import time
from typing import List, Optional
from .errors import AdoAuthenticationError
from .models import Project, Pipeline, CreatePipelineRequest, PipelineRun, RunState, RunResult, PipelinePreviewRequest, PreviewRun, TimelineResponse, TimelineRecord, StepFailure, FailureSummary, LogCollection, LogEntry

logger = logging.getLogger(__name__)


class AdoClient:
    """
    A client for interacting with the Azure DevOps REST API.

    Handles authentication and provides methods for making API requests.

    Args:
        organization_url (str): The URL of the Azure DevOps organization.
        pat (str, optional): A Personal Access Token for authentication.
            If not provided, it will be read from the `AZURE_DEVOPS_EXT_PAT`
            environment variable.

    Raises:
        ValueError: If the Personal Access Token is not provided or found
            in the environment variables.
    """

    def __init__(self, organization_url: str, pat: str = None):
        self.organization_url = organization_url
        if not pat:
            pat = os.environ.get("AZURE_DEVOPS_EXT_PAT")
        if not pat:
            raise ValueError("Personal Access Token (PAT) not provided or found in environment variables.")

        encoded_pat = b64encode(f":{pat}".encode("ascii")).decode("ascii")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {encoded_pat}"
        }
        logger.info("AdoClient initialized.")

    def _validate_response(self, response: requests.Response):
        """
        Checks if the response indicates an authentication failure.

        A common failure mode is receiving the Azure DevOps sign-in page
        in the response body, which indicates an invalid or expired PAT.

        Args:
            response (requests.Response): The HTTP response object.

        Raises:
            AdoAuthenticationError: If the response contains the sign-in page.
        """
        if "Sign In" in response.text:
            logger.error(
                "Authentication failed: Response contains sign-in page. "
                f"Response text: {response.text[:200]}..." # Removed newline character
            )
            raise AdoAuthenticationError(
                "Authentication failed. The response contained a sign-in page, "
                "which likely means the Personal Access Token (PAT) is invalid or expired."
            )

    def _send_request(self, method: str, url: str, **kwargs):
        """
        Sends an authenticated request to the Azure DevOps API.

        This method handles common request logic, including adding authentication
        headers, validating the response, and raising appropriate exceptions
        for HTTP or network errors.

        Args:
            method (str): The HTTP method (e.g., 'GET', 'POST').
            url (str): The full URL for the API endpoint.
            **kwargs: Additional keyword arguments to pass to `requests.request`.

        Returns:
            dict or None: The parsed JSON response from the API, or None if the
            response has no content.

        Raises:
            requests.exceptions.HTTPError: For HTTP-related errors (e.g., 404, 500).
            requests.exceptions.RequestException: For other network-related errors.
        """
        try:
            response = requests.request(method, url, headers=self.headers, **kwargs)
            self._validate_response(response)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            logger.error(f"HTTP Error: {http_err} - Response Body: {http_err.response.text}")
            raise

    def check_authentication(self) -> bool:
        """
        Verifies that the provided credentials are valid.

        This is done by making a lightweight request to a known API endpoint.

        Returns:
            bool: True if the authentication is successful.

        Raises:
            AdoAuthenticationError: If the authentication check fails due to
                an invalid token or other request-related issues.
        """
        # Use a simple, lightweight endpoint to verify the connection.
        # Listing top 1 project is a good candidate.
        url = f"{self.organization_url}/_apis/projects?api-version=7.2-preview.4&$top=1"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            self._validate_response(response)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication check failed with an exception: {e}")
            raise AdoAuthenticationError(f"Authentication check failed: {e}") from e

    def list_projects(self) -> List[Project]:
        """
        Retrieves a list of projects in the organization.

        Returns:
            List[Project]: A list of Project objects.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
        """
        url = f"{self.organization_url}/_apis/projects?api-version=7.2-preview.4"
        logger.info(f"Fetching projects from: {url}")
        response = self._send_request("GET", url)
        projects_data = response.get("value", [])
        logger.info(f"Retrieved {len(projects_data)} projects")
        
        projects = []
        for project_data in projects_data:
            try:
                project = Project(**project_data)
                projects.append(project)
                logger.debug(f"Parsed project: {project.name} (ID: {project.id})")
            except Exception as e:
                logger.error(f"Failed to parse project data: {project_data}. Error: {e}")
                
        return projects

    def list_pipelines(self, project_id: str) -> List[Pipeline]:
        """
        Retrieves a list of pipelines for a given project.

        Args:
            project_id (str): The ID of the project.

        Returns:
            List[Pipeline]: A list of Pipeline objects.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
        """
        url = f"{self.organization_url}/{project_id}/_apis/pipelines?api-version=7.2-preview.1"
        logger.info(f"Fetching pipelines for project {project_id} from: {url}")
        response = self._send_request("GET", url)
        pipelines_data = response.get("value", [])
        logger.info(f"Retrieved {len(pipelines_data)} pipelines for project {project_id}")
        
        if pipelines_data:
            logger.debug(f"First pipeline data: {pipelines_data[0]}")
        
        pipelines = []
        for pipeline_data in pipelines_data:
            try:
                pipeline = Pipeline(**pipeline_data)
                pipelines.append(pipeline)
                logger.debug(f"Parsed pipeline: {pipeline.name} (ID: {pipeline.id})")
            except Exception as e:
                logger.error(f"Failed to parse pipeline data: {pipeline_data}. Error: {e}")
                
        return pipelines

    def create_pipeline(self, project_id: str, request: CreatePipelineRequest) -> Pipeline:
        """
        Creates a new pipeline in the specified project.

        Args:
            project_id (str): The ID of the project.
            request (CreatePipelineRequest): The pipeline creation request.

        Returns:
            Pipeline: The created pipeline object.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
        """
        url = f"{self.organization_url}/{project_id}/_apis/pipelines?api-version=7.2-preview.1"
        logger.info(f"Creating pipeline '{request.name}' in project {project_id}")
        
        # Convert Pydantic model to dict for the request
        request_data = request.model_dump(exclude_none=True)
        logger.debug(f"Pipeline creation request data: {request_data}")
        
        response = self._send_request("POST", url, json=request_data)
        logger.info(f"Successfully created pipeline: {response.get('name')} (ID: {response.get('id')})")
        
        return Pipeline(**response)

    def list_service_connections(self, project_id: str) -> List[dict]:
        """
        Lists service connections for a given project.

        Args:
            project_id (str): The ID of the project.

        Returns:
            List[dict]: A list of service connection objects.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
        """
        url = f"{self.organization_url}/{project_id}/_apis/serviceendpoint/endpoints?api-version=7.2-preview.4"
        logger.info(f"Fetching service connections for project {project_id}")
        response = self._send_request("GET", url)
        connections_data = response.get("value", [])
        logger.info(f"Retrieved {len(connections_data)} service connections for project {project_id}")
        
        if connections_data:
            logger.debug(f"First service connection: {connections_data[0]}")
        
        return connections_data

    def delete_pipeline(self, project_id: str, pipeline_id: int) -> bool:
        """
        Deletes a pipeline (build definition) from the specified project.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline to delete.

        Returns:
            bool: True if deletion was successful, False otherwise.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
        """
        url = f"{self.organization_url}/{project_id}/_apis/build/definitions/{pipeline_id}?api-version=7.1"
        logger.info(f"Deleting pipeline {pipeline_id} from project {project_id}")
        
        try:
            response = requests.delete(url, headers=self.headers, timeout=10)
            self._validate_response(response)
            
            if response.status_code == 204:
                logger.info(f"Successfully deleted pipeline {pipeline_id}")
                return True
            else:
                logger.warning(f"Unexpected status code {response.status_code} when deleting pipeline {pipeline_id}")
                response.raise_for_status()
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to delete pipeline {pipeline_id}: {e}")
            raise

    def get_pipeline(self, project_id: str, pipeline_id: int) -> dict:
        """
        Retrieves details for a specific pipeline.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.

        Returns:
            dict: A dictionary representing the pipeline details.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
        """
        url = f"{self.organization_url}/{project_id}/_apis/pipelines/{pipeline_id}?api-version=7.2-preview.1"
        response = self._send_request("GET", url)
        return response

    def run_pipeline(self, project_id: str, pipeline_id: int) -> PipelineRun:
        """
        Triggers a run for a specific pipeline.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.

        Returns:
            PipelineRun: A PipelineRun object representing the pipeline run details.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
        """
        url = f"{self.organization_url}/{project_id}/_apis/pipelines/{pipeline_id}/runs?api-version=7.2-preview.1"
        logger.info(f"Running pipeline {pipeline_id} in project {project_id}")
        response = self._send_request("POST", url, json={})
        logger.info(f"Pipeline run started: {response.get('id')} with state: {response.get('state')}")
        return PipelineRun(**response)

    def get_pipeline_run(self, project_id: str, pipeline_id: int, run_id: int) -> PipelineRun:
        """
        Retrieves details for a specific pipeline run.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.
            run_id (int): The ID of the pipeline run.

        Returns:
            PipelineRun: A PipelineRun object representing the pipeline run details.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
        """
        url = f"{self.organization_url}/{project_id}/_apis/pipelines/{pipeline_id}/runs/{run_id}?api-version=7.2-preview.1"
        logger.debug(f"Getting pipeline run {run_id} details for project {project_id}")
        response = self._send_request("GET", url)
        logger.debug(f"Pipeline run {run_id} state: {response.get('state')}, result: {response.get('result')}")
        return PipelineRun(**response)

    def preview_pipeline(self, project_id: str, pipeline_id: int, request: Optional[PipelinePreviewRequest] = None) -> PreviewRun:
        """
        Previews a pipeline without executing it, returning the final YAML and other preview information.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.
            request (Optional[PipelinePreviewRequest]): Optional preview request parameters.

        Returns:
            PreviewRun: A PreviewRun object representing the pipeline preview details.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
        """
        url = f"{self.organization_url}/{project_id}/_apis/pipelines/{pipeline_id}/preview?api-version=7.2-preview.1"
        logger.info(f"Previewing pipeline {pipeline_id} in project {project_id}")
        
        # Use the request data if provided, otherwise send an empty preview request
        request_data = {}
        if request:
            request_data = request.model_dump(exclude_none=True)
        
        logger.debug(f"Pipeline preview request data: {request_data}")
        response = self._send_request("POST", url, json=request_data)
        logger.info(f"Pipeline preview completed for pipeline {pipeline_id}")
        return PreviewRun(**response)

    def wait_for_pipeline_completion(
        self, 
        project_id: str, 
        pipeline_id: int,
        run_id: int, 
        timeout_seconds: int = 300, 
        poll_interval_seconds: int = 10
    ) -> PipelineRun:
        """
        Waits for a pipeline run to complete by polling its status.

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

    def list_pipeline_logs(self, project_id: str, pipeline_id: int, run_id: int) -> LogCollection:
        """
        Lists logs for a specific pipeline run.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.
            run_id (int): The ID of the pipeline run.

        Returns:
            LogCollection: A collection of log entries for the pipeline run.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
        """
        url = f"{self.organization_url}/{project_id}/_apis/pipelines/{pipeline_id}/runs/{run_id}/logs?api-version=7.2-preview.1"
        logger.info(f"Listing logs for pipeline run {run_id} in project {project_id}")
        response = self._send_request("GET", url)
        logger.info(f"Retrieved {len(response.get('logs', []))} logs for run {run_id}")
        return LogCollection(**response)

    def get_log_content_by_id(self, project_id: str, pipeline_id: int, run_id: int, log_id: int) -> str:
        """
        Gets the content of a specific log from a pipeline run.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.
            run_id (int): The ID of the pipeline run.
            log_id (int): The ID of the specific log.

        Returns:
            str: The log content as a string.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
        """
        # Get log metadata with signed content URL
        url = f"{self.organization_url}/{project_id}/_apis/pipelines/{pipeline_id}/runs/{run_id}/logs/{log_id}?$expand=signedContent&api-version=7.2-preview.1"
        logger.info(f"Getting log content for log {log_id} from run {run_id}")
        response = self._send_request("GET", url)
        
        # Extract and fetch content from signed URL
        if 'signedContent' in response and 'url' in response['signedContent']:
            import requests
            signed_url = response['signedContent']['url']
            content_response = requests.get(signed_url)
            content_response.raise_for_status()
            logger.info(f"Retrieved log content ({len(content_response.text)} characters) for log {log_id}")
            return content_response.text
        
        logger.warning(f"No signed content URL found for log {log_id}")
        return ""

    def get_pipeline_timeline(self, project_id: str, pipeline_id: int, run_id: int) -> TimelineResponse:
        """
        Gets the build timeline for a pipeline run, showing status of all stages, jobs, and tasks.

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
        url = f"{self.organization_url}/{project_id}/_apis/build/builds/{run_id}/timeline?api-version=7.2-preview.2"
        logger.info(f"Getting timeline for pipeline run {run_id} in project {project_id}")
        response = self._send_request("GET", url)
        logger.info(f"Retrieved timeline with {len(response.get('records', []))} records for run {run_id}")
        return TimelineResponse(**response)

    def get_pipeline_failure_summary(self, project_id: str, pipeline_id: int, run_id: int) -> FailureSummary:
        """
        Gets a comprehensive summary of pipeline failures, including root causes and affected components.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.
            run_id (int): The ID of the pipeline run.

        Returns:
            FailureSummary: Detailed summary of failures with log content for root causes.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
        """
        logger.info(f"Analyzing failures for pipeline run {run_id}")
        
        # Get the timeline to identify failed steps
        timeline = self.get_pipeline_timeline(project_id, pipeline_id, run_id)
        
        # Find all failed records
        failed_records = [record for record in timeline.records if record.result == 'failed']
        
        # Separate root causes (Tasks) from hierarchy failures (Jobs, Stages)
        root_cause_tasks = []
        hierarchy_failures = []
        
        for record in failed_records:
            # Extract issues as strings
            issues = []
            if record.issues:
                issues = [issue.get('message', 'Unknown error') for issue in record.issues]
            
            step_failure = StepFailure(
                step_name=record.name or 'Unknown Step',
                step_type=record.type or 'Unknown',
                result=record.result or 'failed',
                log_id=record.log.get('id') if record.log else None,
                issues=issues,
                start_time=record.startTime,
                finish_time=record.finishTime
            )
            
            # Get log content for tasks with logs
            if record.type == 'Task' and step_failure.log_id:
                try:
                    step_failure.log_content = self.get_log_content_by_id(
                        project_id, pipeline_id, run_id, step_failure.log_id
                    )
                except Exception as e:
                    logger.warning(f"Failed to get log content for step {record.name}: {e}")
                    step_failure.log_content = f"Error retrieving log: {e}"
            
            # Categorize failures
            if record.type == 'Task':
                root_cause_tasks.append(step_failure)
            else:
                hierarchy_failures.append(step_failure)
        
        # Get pipeline URL from the run
        pipeline_run = self.get_pipeline_run(project_id, pipeline_id, run_id)
        pipeline_url = None
        if hasattr(pipeline_run, '_links') and pipeline_run._links:
            pipeline_url = pipeline_run._links.get('web', {}).get('href')
        
        total_failed = len(failed_records)
        logger.info(f"Found {total_failed} failed steps: {len(root_cause_tasks)} root causes, {len(hierarchy_failures)} hierarchy failures")
        
        return FailureSummary(
            total_failed_steps=total_failed,
            root_cause_tasks=root_cause_tasks,
            hierarchy_failures=hierarchy_failures,
            pipeline_url=pipeline_url,
            build_id=run_id
        )

    def get_failed_step_logs(self, project_id: str, pipeline_id: int, run_id: int, step_name: Optional[str] = None) -> List[StepFailure]:
        """
        Gets detailed log information for failed steps, optionally filtered by step name.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.
            run_id (int): The ID of the pipeline run.
            step_name (Optional[str]): Filter to specific step name (case-insensitive partial match).

        Returns:
            List[StepFailure]: List of failed steps with their log content.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
        """
        logger.info(f"Getting failed step logs for run {run_id}" + (f" (filter: {step_name})" if step_name else ""))
        
        # Get failure summary which includes log content for root causes
        failure_summary = self.get_pipeline_failure_summary(project_id, pipeline_id, run_id)
        
        # Combine all failed steps
        all_failures = failure_summary.root_cause_tasks + failure_summary.hierarchy_failures
        
        # Filter by step name if provided
        if step_name:
            step_name_lower = step_name.lower()
            filtered_failures = [
                failure for failure in all_failures 
                if step_name_lower in failure.step_name.lower()
            ]
            logger.info(f"Filtered to {len(filtered_failures)} steps matching '{step_name}'")
            return filtered_failures
        
        return all_failures
