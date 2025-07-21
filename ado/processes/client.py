"""Client for Azure DevOps Processes and Templates operations."""

import logging
from typing import List, Optional

from ado.cache import ado_cache
from ado.client import AdoClient
from ado.errors import AdoError
from .models import Process, ProcessTemplate, WorkItemTemplate, ProjectProcessInfo, TeamInfo

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
        """
        Get the process template ID for a project.

        Args:
            project_id: The ID or name of the project

        Returns:
            str: The process template ID (UUID)

        Raises:
            AdoError: If the API call fails
        """
        logger.info(f"Getting process ID for project '{project_id}'")

        # Check cache first
        cache_key = f"project_process_id:{project_id}"
        cached_result = ado_cache._get(cache_key)
        if cached_result:
            logger.info(
                f"Retrieved process ID from cache for project '{project_id}': {cached_result}"
            )
            return cached_result

        try:
            # Get project properties to find the process template ID
            response = self.client._send_request(
                method="GET",
                url=f"{self.client.organization_url}/_apis/projects/{project_id}/properties",
                params={"api-version": "7.1-preview.1"},
            )

            properties = response.get("value", [])
            process_id = None

            # Look for the current process template ID in properties
            for prop in properties:
                if prop.get("name") == "System.CurrentProcessTemplateId":
                    process_id = prop.get("value")
                    break

            if not process_id:
                # Fallback: try original process template ID
                for prop in properties:
                    if prop.get("name") == "System.OriginalProcessTemplateId":
                        process_id = prop.get("value")
                        break

            if not process_id:
                raise AdoError(
                    f"Could not find process template ID for project '{project_id}'",
                    "process_id_not_found",
                )

            # Cache the result for 1 hour
            ado_cache._set(cache_key, process_id, 3600)

            logger.info(
                f"Successfully retrieved process ID for project '{project_id}': {process_id}"
            )
            return process_id

        except Exception as e:
            logger.error(f"Failed to get process ID for project '{project_id}': {e}")
            raise AdoError(
                f"Failed to get process ID for project '{project_id}': {e}", "get_process_id_failed"
            ) from e

    def get_project_process_info(self, project_id: str) -> ProjectProcessInfo:
        """
        Get comprehensive process information for a project.

        Args:
            project_id: The ID or name of the project

        Returns:
            ProjectProcessInfo: Complete process information

        Raises:
            AdoError: If the API call fails
        """
        logger.info(f"Getting process info for project '{project_id}'")

        # Check cache first
        cache_key = f"project_process_info:{project_id}"
        cached_result = ado_cache._get(cache_key)
        if cached_result:
            logger.info(f"Retrieved process info from cache for project '{project_id}'")
            return ProjectProcessInfo(**cached_result)

        try:
            # Get project properties
            response = self.client._send_request(
                method="GET",
                url=f"{self.client.organization_url}/_apis/projects/{project_id}/properties",
                params={"api-version": "7.1-preview.1"},
            )

            properties = response.get("value", [])
            process_info = {
                "projectId": project_id,
                "currentProcessTemplateId": None,
                "originalProcessTemplateId": None,
                "processTemplateName": None,
                "processTemplateType": None,
            }

            # Extract process-related properties
            for prop in properties:
                name = prop.get("name", "")
                value = prop.get("value")

                if name == "System.CurrentProcessTemplateId":
                    process_info["currentProcessTemplateId"] = value
                elif name == "System.OriginalProcessTemplateId":
                    process_info["originalProcessTemplateId"] = value
                elif name == "System.Process Template":
                    process_info["processTemplateName"] = value
                elif name == "System.ProcessTemplateType":
                    process_info["processTemplateType"] = value

            if not process_info["currentProcessTemplateId"]:
                raise AdoError(
                    f"Could not find process template ID for project '{project_id}'",
                    "process_id_not_found",
                )

            result = ProjectProcessInfo(**process_info)

            # Cache the result for 1 hour
            ado_cache._set(cache_key, result.model_dump(), 3600)

            logger.info(
                f"Successfully retrieved process info for project '{project_id}': {result.processTemplateName}"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to get process info for project '{project_id}': {e}")
            raise AdoError(
                f"Failed to get process info for project '{project_id}': {e}",
                "get_process_info_failed",
            ) from e

    def list_processes(self) -> List[Process]:
        """
        List all available process templates in the organization.

        Returns:
            List[Process]: List of available processes

        Raises:
            AdoError: If the API call fails
        """
        logger.info("Listing available processes")

        # Check cache first
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
                    process = Process(**process_data)
                    processes.append(process)
                except Exception as e:
                    logger.warning(f"Failed to parse process data: {process_data}, error: {e}")
                    continue

            # Cache the result for 1 hour
            ado_cache._set(cache_key, [p.model_dump() for p in processes], 3600)

            logger.info(f"Successfully retrieved {len(processes)} processes")
            return processes

        except Exception as e:
            logger.error(f"Failed to list processes: {e}")
            raise AdoError(f"Failed to list processes: {e}", "list_processes_failed") from e

    def get_process_details(self, process_id: str) -> Process:
        """
        Get detailed information about a specific process.

        This method handles both base process templates and custom/inherited processes.
        If a specific process ID is not found, it attempts to find the base process.

        Args:
            process_id: The process template ID

        Returns:
            Process: Detailed process information

        Raises:
            AdoError: If the API call fails
        """
        logger.info(f"Getting process details for process '{process_id}'")

        # Check cache first
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

            # Map the response fields to our Process model
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

            # Cache the result for 1 hour
            ado_cache._set(cache_key, process.model_dump(), 3600)

            logger.info(
                f"Successfully retrieved process details for '{process.name}' ({process_id})"
            )
            return process

        except Exception as e:
            # If process not found, it might be a custom process template
            # Try to find a base process with matching information
            # Handle both 404 (Not Found) and 400 (Bad Request) for custom process templates
            # But exclude obviously invalid process IDs like all zeros
            is_not_found_error = "404" in str(e) or "not found" in str(e).lower()
            is_bad_request_error = "400" in str(e) or "bad request" in str(e).lower()
            is_zero_uuid = process_id == "00000000-0000-0000-0000-000000000000"

            if is_not_found_error or (is_bad_request_error and not is_zero_uuid):
                logger.warning(
                    f"Process '{process_id}' not accessible via process API (likely custom template), attempting fallback"
                )

                try:
                    # Try to find project information that uses this process to get the name
                    process_name = "Custom Process Template"
                    base_process_type = "custom"

                    # Try to get projects and find one that uses this process ID to get the actual name
                    try:
                        projects_response = self.client._send_request(
                            method="GET",
                            url=f"{self.client.organization_url}/_apis/projects",
                            params={"api-version": "7.1"},
                        )

                        projects = projects_response.get("value", [])

                        # Check each project to find one that uses this process
                        for project in projects[
                            :10
                        ]:  # Limit to first 10 projects to avoid too many calls
                            try:
                                project_process_info = self.get_project_process_info(project["id"])
                                if project_process_info.currentProcessTemplateId == process_id:
                                    if project_process_info.processTemplateName:
                                        process_name = project_process_info.processTemplateName
                                        logger.info(
                                            f"Found process name '{process_name}' from project '{project['name']}'"
                                        )
                                        break
                            except Exception as project_error:
                                # Skip this project and try the next one
                                continue

                    except Exception as projects_error:
                        logger.debug(
                            f"Could not retrieve projects list for process name lookup: {projects_error}"
                        )

                    process_data = {
                        "id": process_id,
                        "name": process_name,
                        "description": f"Custom or inherited process template (ID: {process_id})",
                        "type": base_process_type,
                        "isDefault": False,
                        "isEnabled": True,
                        "customizationType": "custom",
                    }

                    process = Process(**process_data)

                    # Cache the result for 1 hour
                    ado_cache._set(cache_key, process.model_dump(), 3600)

                    logger.info(
                        f"Created fallback process details for custom process '{process_name}' ({process_id})"
                    )
                    return process

                except Exception as fallback_error:
                    logger.error(f"Failed to create fallback process details: {fallback_error}")
                    # Fall through to original error

            logger.error(f"Failed to get process details for process '{process_id}': {e}")
            raise AdoError(
                f"Failed to get process details for process '{process_id}': {e}",
                "get_process_details_failed",
            ) from e

    def get_default_team_id(self, project_id: str) -> str:
        """
        Get the default team ID for a project.

        Args:
            project_id: The ID or name of the project

        Returns:
            str: The default team ID

        Raises:
            AdoError: If the API call fails
        """
        logger.info(f"Getting default team ID for project '{project_id}'")

        # Check cache first
        cache_key = f"default_team_id:{project_id}"
        cached_result = ado_cache._get(cache_key)
        if cached_result:
            logger.info(
                f"Retrieved default team ID from cache for project '{project_id}': {cached_result}"
            )
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

            # Find the default team (usually has the same name as the project)
            default_team_id = None
            for team in teams:
                team_name = team.get("name", "")
                team_id = team.get("id", "")

                # Default team typically matches project name or is first team
                if not default_team_id:
                    default_team_id = team_id

                # If team name matches project, prefer that
                if team_name == project_id:
                    default_team_id = team_id
                    break

            if not default_team_id:
                raise AdoError(
                    f"Could not determine default team for project '{project_id}'",
                    "default_team_not_found",
                )

            # Cache the result for 1 hour
            ado_cache._set(cache_key, default_team_id, 3600)

            logger.info(
                f"Successfully retrieved default team ID for project '{project_id}': {default_team_id}"
            )
            return default_team_id

        except Exception as e:
            logger.error(f"Failed to get default team ID for project '{project_id}': {e}")
            raise AdoError(
                f"Failed to get default team ID for project '{project_id}': {e}",
                "get_default_team_failed",
            ) from e

    def get_work_item_templates(
        self, project_id: str, team_id: Optional[str] = None, work_item_type: Optional[str] = None
    ) -> List[WorkItemTemplate]:
        """
        Get work item templates for a team.

        Args:
            project_id: The ID or name of the project
            team_id: The team ID (if None, uses default team)
            work_item_type: Optional filter by work item type

        Returns:
            List[WorkItemTemplate]: List of available templates

        Raises:
            AdoError: If the API call fails
        """
        if not team_id:
            team_id = self.get_default_team_id(project_id)

        logger.info(f"Getting work item templates for project '{project_id}', team '{team_id}'")

        # Check cache first
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
                    template = WorkItemTemplate(**template_data)
                    templates.append(template)
                except Exception as e:
                    logger.warning(f"Failed to parse template data: {template_data}, error: {e}")
                    continue

            # Cache the result for 1 hour
            ado_cache._set(cache_key, [t.model_dump() for t in templates], 3600)

            logger.info(f"Successfully retrieved {len(templates)} work item templates")
            return templates

        except Exception as e:
            logger.error(f"Failed to get work item templates: {e}")
            raise AdoError(f"Failed to get work item templates: {e}", "get_templates_failed") from e

    def get_work_item_template(
        self, project_id: str, template_id: str, team_id: Optional[str] = None
    ) -> WorkItemTemplate:
        """
        Get detailed information about a specific work item template.

        Args:
            project_id: The ID or name of the project
            template_id: The template ID
            team_id: The team ID (if None, uses default team)

        Returns:
            WorkItemTemplate: Detailed template information

        Raises:
            AdoError: If the API call fails
        """
        if not team_id:
            team_id = self.get_default_team_id(project_id)

        logger.info(
            f"Getting work item template '{template_id}' for project '{project_id}', team '{team_id}'"
        )

        # Check cache first
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

            # Cache the result for 1 hour
            ado_cache._set(cache_key, template.model_dump(), 3600)

            logger.info(f"Successfully retrieved template '{template.name}' ({template_id})")
            return template

        except Exception as e:
            logger.error(f"Failed to get work item template '{template_id}': {e}")
            raise AdoError(
                f"Failed to get work item template '{template_id}': {e}", "get_template_failed"
            ) from e
