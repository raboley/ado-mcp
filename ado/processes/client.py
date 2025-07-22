"""Client for Azure DevOps Processes and Templates operations."""

import logging
from typing import List, Optional

from ado.cache import ado_cache
from ado.client import AdoClient
from ado.errors import AdoError
from .models import Process, ProcessTemplate, WorkItemTemplate, ProjectProcessInfo, TeamInfo
from .utils import (
    handle_api_error, extract_process_properties, find_default_team, 
    create_fallback_process, find_process_name_from_projects, is_recoverable_process_error
)

logger = logging.getLogger(__name__)


class ProcessesClient:
    """
    Client for Azure DevOps Processes and Templates operations.

    Provides methods for:
    - Getting project process information
    - Listing available processes and process templates
    - Getting detailed process information
    - Managing work item templates
    """

    def __init__(self, client: AdoClient):
        """
        Initialize ProcessesClient.

        Args:
            client: The ADO client instance
        """
        self.client = client

    def get_project_process_id(self, project_id: str) -> str:
        """Get the process template ID for a project."""
        logger.info(f"Getting process ID for project '{project_id}'")

        cache_key = f"project_process_id:{project_id}"
        cached_result = ado_cache._get(cache_key)
        if cached_result:
            logger.info(f"Retrieved process ID from cache for project '{project_id}': {cached_result}")
            return cached_result

        try:
            response = self.client._send_request(
                method="GET",
                url=f"{self.client.organization_url}/_apis/projects/{project_id}/properties",
                params={"api-version": "7.1-preview.1"},
            )

            properties = response.get("value", [])
            process_props = extract_process_properties(properties)
            
            process_id = process_props["currentProcessTemplateId"] or process_props["originalProcessTemplateId"]
            if not process_id:
                raise AdoError(
                    f"Could not find process template ID for project '{project_id}'",
                    "process_id_not_found",
                )

            ado_cache._set(cache_key, process_id, 3600)
            logger.info(f"Successfully retrieved process ID for project '{project_id}': {process_id}")
            return process_id

        except Exception as e:
            handle_api_error("get process ID", f"project '{project_id}'", e)

    def get_project_process_info(self, project_id: str) -> ProjectProcessInfo:
        """Get comprehensive process information for a project."""
        logger.info(f"Getting process info for project '{project_id}'")

        cache_key = f"project_process_info:{project_id}"
        cached_result = ado_cache._get(cache_key)
        if cached_result:
            logger.info(f"Retrieved process info from cache for project '{project_id}'")
            return ProjectProcessInfo(**cached_result)

        try:
            response = self.client._send_request(
                method="GET",
                url=f"{self.client.organization_url}/_apis/projects/{project_id}/properties",
                params={"api-version": "7.1-preview.1"},
            )

            properties = response.get("value", [])
            process_props = extract_process_properties(properties)
            
            if not process_props["currentProcessTemplateId"]:
                raise AdoError(
                    f"Could not find process template ID for project '{project_id}'",
                    "process_id_not_found",
                )

            process_info = {"projectId": project_id, **process_props}
            result = ProjectProcessInfo(**process_info)

            ado_cache._set(cache_key, result.model_dump(), 3600)
            logger.info(f"Successfully retrieved process info for project '{project_id}': {result.processTemplateName}")
            return result

        except Exception as e:
            handle_api_error("get process info", f"project '{project_id}'", e)

    def list_processes(self) -> List[Process]:
        """List all available process templates in the organization."""
        logger.info("Listing available processes")

        cache_key = "processes_list"
        cached_result = ado_cache._get(cache_key)
        if cached_result:
            logger.info(f"Retrieved {len(cached_result)} processes from cache")
            return [Process(**process) for process in cached_result]

        try:
            response = self.client._send_request(
                method="GET",
                url=f"{self.client.organization_url}/_apis/process/processes",
                params={"api-version": "7.1"},
            )

            processes_data = response.get("value", [])
            processes = []

            for process_data in processes_data:
                try:
                    processes.append(Process(**process_data))
                except Exception as e:
                    logger.warning(f"Failed to parse process data: {process_data}, error: {e}")

            ado_cache._set(cache_key, [p.model_dump() for p in processes], 3600)
            logger.info(f"Successfully retrieved {len(processes)} processes")
            return processes

        except Exception as e:
            handle_api_error("list processes", "organization", e)

    def get_process_details(self, process_id: str) -> Process:
        """Get detailed information about a specific process."""
        logger.info(f"Getting process details for process '{process_id}'")

        cache_key = f"process_details:{process_id}"
        cached_result = ado_cache._get(cache_key)
        if cached_result:
            logger.info(f"Retrieved process details from cache for process '{process_id}'")
            return Process(**cached_result)

        try:
            response = self.client._send_request(
                method="GET",
                url=f"{self.client.organization_url}/_apis/work/processes/{process_id}",
                params={"api-version": "7.1"},
            )

            process_data = {
                "id": response.get("typeId", process_id),
                "name": response.get("name", ""),
                "description": response.get("description"),
                "type": response.get("customizationType"),
                "isDefault": response.get("isDefault"),
                "isEnabled": response.get("isEnabled"),
                "customizationType": response.get("customizationType"),
                "parentProcessTypeId": response.get("parentProcessTypeId"),
                "url": response.get("url"),
                "_links": response.get("_links"),
            }

            process = Process(**process_data)
            ado_cache._set(cache_key, process.model_dump(), 3600)
            logger.info(f"Successfully retrieved process details for '{process.name}' ({process_id})")
            return process

        except Exception as e:
            if is_recoverable_process_error(e, process_id):
                logger.warning(f"Process '{process_id}' not accessible via process API (likely custom template), attempting fallback")
                
                try:
                    process_name = find_process_name_from_projects(self.client, process_id)
                    process_data = create_fallback_process(process_id, process_name)
                    process = Process(**process_data)
                    
                    ado_cache._set(cache_key, process.model_dump(), 3600)
                    logger.info(f"Created fallback process details for custom process '{process_name}' ({process_id})")
                    return process
                    
                except Exception as fallback_error:
                    logger.error(f"Failed to create fallback process details: {fallback_error}")

            handle_api_error("get process details", f"process '{process_id}'", e)

    def get_default_team_id(self, project_id: str) -> str:
        """Get the default team ID for a project."""
        logger.info(f"Getting default team ID for project '{project_id}'")

        cache_key = f"default_team_id:{project_id}"
        cached_result = ado_cache._get(cache_key)
        if cached_result:
            logger.info(f"Retrieved default team ID from cache for project '{project_id}': {cached_result}")
            return cached_result

        try:
            response = self.client._send_request(
                method="GET",
                url=f"{self.client.organization_url}/_apis/projects/{project_id}/teams",
                params={"api-version": "7.1"},
            )

            teams = response.get("value", [])
            if not teams:
                raise AdoError(f"No teams found for project '{project_id}'", "no_teams_found")

            default_team_id = find_default_team(teams, project_id)
            if not default_team_id:
                raise AdoError(
                    f"Could not determine default team for project '{project_id}'",
                    "default_team_not_found",
                )

            ado_cache._set(cache_key, default_team_id, 3600)
            logger.info(f"Successfully retrieved default team ID for project '{project_id}': {default_team_id}")
            return default_team_id

        except Exception as e:
            handle_api_error("get default team ID", f"project '{project_id}'", e)

    def get_work_item_templates(
        self, project_id: str, team_id: Optional[str] = None, work_item_type: Optional[str] = None
    ) -> List[WorkItemTemplate]:
        """Get work item templates for a team."""
        if not team_id:
            team_id = self.get_default_team_id(project_id)

        logger.info(f"Getting work item templates for project '{project_id}', team '{team_id}'")

        cache_key = f"work_item_templates:{project_id}:{team_id}:{work_item_type or 'all'}"
        cached_result = ado_cache._get(cache_key)
        if cached_result:
            logger.info(f"Retrieved {len(cached_result)} templates from cache")
            return [WorkItemTemplate(**template) for template in cached_result]

        try:
            params = {"api-version": "7.1"}
            if work_item_type:
                params["workitemtypename"] = work_item_type

            response = self.client._send_request(
                method="GET",
                url=f"{self.client.organization_url}/{project_id}/{team_id}/_apis/wit/templates",
                params=params,
            )

            templates_data = response.get("value", [])
            templates = []

            for template_data in templates_data:
                try:
                    templates.append(WorkItemTemplate(**template_data))
                except Exception as e:
                    logger.warning(f"Failed to parse template data: {template_data}, error: {e}")

            ado_cache._set(cache_key, [t.model_dump() for t in templates], 3600)
            logger.info(f"Successfully retrieved {len(templates)} work item templates")
            return templates

        except Exception as e:
            handle_api_error("get work item templates", f"project '{project_id}', team '{team_id}'", e)

    def get_work_item_template(
        self, project_id: str, template_id: str, team_id: Optional[str] = None
    ) -> WorkItemTemplate:
        """Get detailed information about a specific work item template."""
        if not team_id:
            team_id = self.get_default_team_id(project_id)

        logger.info(f"Getting work item template '{template_id}' for project '{project_id}', team '{team_id}'")

        cache_key = f"work_item_template:{project_id}:{team_id}:{template_id}"
        cached_result = ado_cache._get(cache_key)
        if cached_result:
            logger.info(f"Retrieved template details from cache for template '{template_id}'")
            return WorkItemTemplate(**cached_result)

        try:
            response = self.client._send_request(
                method="GET",
                url=f"{self.client.organization_url}/{project_id}/{team_id}/_apis/wit/templates/{template_id}",
                params={"api-version": "7.1"},
            )

            template = WorkItemTemplate(**response)
            ado_cache._set(cache_key, template.model_dump(), 3600)
            logger.info(f"Successfully retrieved template '{template.name}' ({template_id})")
            return template

        except Exception as e:
            handle_api_error("get work item template", f"template '{template_id}'", e)
