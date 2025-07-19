"""Pipeline CRUD operations."""

import logging
import re

import requests
from opentelemetry import trace
import yaml

from ..models import CreatePipelineRequest, Pipeline, PipelinePreviewRequest, PreviewRun

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class PipelineOperations:
    """Azure DevOps pipeline CRUD operations."""

    def __init__(self, client_core):
        """Initialize with reference to core client."""
        self._client = client_core

    def list_pipelines(self, project_id: str) -> list[Pipeline]:
        """
        Retrieve a list of pipelines for a given project.

        Args:
            project_id (str): The ID of the project.

        Returns:
            List[Pipeline]: A list of Pipeline objects.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
        """
        with tracer.start_as_current_span("ado_list_pipelines") as span:
            span.set_attribute("ado.operation", "list_pipelines")
            span.set_attribute("ado.project_id", project_id)
            
            url = f"{self._client.organization_url}/{project_id}/_apis/pipelines?api-version=7.2-preview.1"
            logger.info(f"Fetching pipelines for project {project_id} from: {url}")
            response = self._client._send_request("GET", url)
            pipelines_data = response.get("value", [])
            
            span.set_attribute("ado.pipelines_count", len(pipelines_data))
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
                    span.record_exception(e)

            return pipelines

    def create_pipeline(self, project_id: str, request: CreatePipelineRequest) -> Pipeline:
        """
        Create a new pipeline in the specified project.

        Args:
            project_id (str): The ID of the project.
            request (CreatePipelineRequest): The pipeline creation request.

        Returns:
            Pipeline: The created pipeline object.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
        """
        url = f"{self._client.organization_url}/{project_id}/_apis/pipelines?api-version=7.2-preview.1"
        logger.info(f"Creating pipeline '{request.name}' in project {project_id}")

        # Convert Pydantic model to dict for the request
        request_data = request.model_dump(exclude_none=True)
        logger.debug(f"Pipeline creation request data: {request_data}")

        response = self._client._send_request("POST", url, json=request_data)
        logger.info(
            f"Successfully created pipeline: {response.get('name')} (ID: {response.get('id')})"
        )

        return Pipeline(**response)

    def delete_pipeline(self, project_id: str, pipeline_id: int) -> bool:
        """
        Delete a pipeline (build definition) from the specified project.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline to delete.

        Returns:
            bool: True if deletion was successful, False otherwise.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
        """
        url = f"{self._client.organization_url}/{project_id}/_apis/build/definitions/{pipeline_id}?api-version=7.1"
        logger.info(f"Deleting pipeline {pipeline_id} from project {project_id}")

        try:
            response = requests.delete(url, headers=self._client.headers, timeout=10)
            self._client._validate_response(response)

            if response.status_code == 204:
                logger.info(f"Successfully deleted pipeline {pipeline_id}")
                return True
            else:
                logger.warning(
                    f"Unexpected status code {response.status_code} when deleting pipeline {pipeline_id}"
                )
                response.raise_for_status()
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to delete pipeline {pipeline_id}: {e}")
            raise

    def get_pipeline(self, project_id: str, pipeline_id: int) -> dict:
        """
        Retrieve details for a specific pipeline.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.

        Returns:
            dict: A dictionary representing the pipeline details.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
        """
        url = f"{self._client.organization_url}/{project_id}/_apis/pipelines/{pipeline_id}?api-version=7.2-preview.1"
        logger.debug(f"Getting pipeline {pipeline_id} details for project {project_id}")
        response = self._client._send_request("GET", url)
        logger.debug(f"Pipeline {pipeline_id} name: {response.get('name')}")
        return response

    def preview_pipeline(
        self, project_id: str, pipeline_id: int, request: PipelinePreviewRequest | None = None
    ) -> PreviewRun:
        """
        Preview a pipeline without executing it, returning the final YAML and other preview information.

        Args:
            project_id (str): The ID of the project.
            pipeline_id (int): The ID of the pipeline.
            request (Optional[PipelinePreviewRequest]): Optional preview request parameters.

        Returns:
            PreviewRun: A PreviewRun object representing the pipeline preview details.

        Raises:
            requests.exceptions.RequestException: For network-related errors.
        """
        url = f"{self._client.organization_url}/{project_id}/_apis/pipelines/{pipeline_id}/preview?api-version=7.2-preview.1"
        logger.info(f"Previewing pipeline {pipeline_id} in project {project_id}")

        request_data = {}
        if request:
            request_data = request.model_dump(exclude_none=True)

        logger.debug(f"Pipeline preview request data: {request_data}")
        response = self._client._send_request("POST", url, json=request_data)
        logger.info(f"Pipeline preview completed for pipeline {pipeline_id}")
        
        # Update the finalYaml to reflect user's resource parameters if provided
        if request and request.resources:
            resources_data = request_data.get("resources", {})
            if "repositories" in resources_data:
                final_yaml = response.get("finalYaml", "")
                if final_yaml:
                    logger.info(f"Updating YAML resources with user parameters: {resources_data}")
                    final_yaml = self._update_yaml_resources(final_yaml, resources_data)
                    response["finalYaml"] = final_yaml
        
        return PreviewRun(**response)
    
    def _update_yaml_resources(self, final_yaml: str, resources: dict) -> str:
        """
        Update the finalYaml to reflect the user's resource parameters.
        NOTE: This only exists because for some reason ADO does not already do this
        When it returns YAML to the user via the Preview API, and it would cause confusion
        of what branches were used if we didn't make this patch.
        
        Args:
            final_yaml (str): The original final YAML from Azure DevOps
            resources (dict): The resources parameters from the user's request
            
        Returns:
            str: Updated YAML with user's resource parameters reflected
        """
        try:
            yaml_data = yaml.safe_load(final_yaml)
            
            if "repositories" in resources and "resources" in yaml_data:
                if "repositories" in yaml_data["resources"]:
                    # yaml_data["resources"]["repositories"] is a list of repo dictionaries
                    for repo_data in yaml_data["resources"]["repositories"]:
                        repo_name = repo_data.get("repository")
                        if repo_name and repo_name in resources["repositories"]:
                            user_repo_params = resources["repositories"][repo_name]
                            
                            if "refName" in user_repo_params:
                                repo_data["ref"] = user_repo_params["refName"]
                            
                            logger.debug(f"Updated repository '{repo_name}' with user parameters: {user_repo_params}")
            
            return yaml.dump(yaml_data, default_flow_style=False, sort_keys=False)
            
        except Exception as e:
            logger.warning(f"Failed to update YAML resources: {e}")
            return final_yaml
