"""Utility functions for processes client operations."""

import logging
from typing import Any, Dict, List, Optional, TypeVar, Callable
from ado.cache import ado_cache
from ado.errors import AdoError

logger = logging.getLogger(__name__)

T = TypeVar('T')


def with_cache(cache_key: str, ttl: int = 3600):
    """Decorator for caching method results."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args, **kwargs) -> T:
            cached_result = ado_cache._get(cache_key)
            if cached_result:
                logger.info(f"Retrieved from cache: {cache_key}")
                return cached_result
            
            result = func(*args, **kwargs)
            ado_cache._set(cache_key, result, ttl)
            return result
        return wrapper
    return decorator


def handle_api_error(operation: str, resource: str, error: Exception) -> None:
    """Standard error handling for API operations."""
    logger.error(f"Failed to {operation} for {resource}: {error}")
    raise AdoError(f"Failed to {operation} for {resource}: {error}", f"{operation}_failed") from error


def extract_process_properties(properties: List[Dict[str, Any]]) -> Dict[str, Optional[str]]:
    """Extract process-related properties from project properties."""
    process_info = {
        "currentProcessTemplateId": None,
        "originalProcessTemplateId": None, 
        "processTemplateName": None,
        "processTemplateType": None,
    }
    
    property_mappings = {
        "System.CurrentProcessTemplateId": "currentProcessTemplateId",
        "System.OriginalProcessTemplateId": "originalProcessTemplateId",
        "System.Process Template": "processTemplateName",
        "System.ProcessTemplateType": "processTemplateType",
    }
    
    for prop in properties:
        name = prop.get("name", "")
        if name in property_mappings:
            process_info[property_mappings[name]] = prop.get("value")
    
    return process_info


def find_default_team(teams: List[Dict[str, Any]], project_id: str) -> Optional[str]:
    """Find the default team ID from a list of teams."""
    if not teams:
        return None
    
    default_team_id = teams[0].get("id")  # Fallback to first team
    
    # Prefer team with name matching project
    for team in teams:
        if team.get("name") == project_id:
            return team.get("id")
    
    return default_team_id


def create_fallback_process(process_id: str, process_name: str = "Custom Process Template") -> Dict[str, Any]:
    """Create fallback process data for custom/inherited processes."""
    return {
        "id": process_id,
        "name": process_name,
        "description": f"Custom or inherited process template (ID: {process_id})",
        "type": "custom",
        "isDefault": False,
        "isEnabled": True,
        "customizationType": "custom",
    }


def find_process_name_from_projects(client, process_id: str, max_projects: int = 10) -> str:
    """Find process name by checking projects that use this process ID."""
    try:
        projects_response = client._send_request(
            method="GET",
            url=f"{client.organization_url}/_apis/projects",
            params={"api-version": "7.1"},
        )

        projects = projects_response.get("value", [])[:max_projects]
        
        for project in projects:
            try:
                # Import here to avoid circular imports
                from .client import ProcessesClient
                processes_client = ProcessesClient(client)
                project_process_info = processes_client.get_project_process_info(project["id"])
                if project_process_info.currentProcessTemplateId == process_id:
                    if project_process_info.processTemplateName:
                        logger.info(f"Found process name '{project_process_info.processTemplateName}' from project '{project['name']}'")
                        return project_process_info.processTemplateName
            except Exception:
                continue  # Skip this project and try the next one
                
    except Exception as e:
        logger.debug(f"Could not retrieve projects list for process name lookup: {e}")
    
    return "Custom Process Template"


def is_recoverable_process_error(error: Exception, process_id: str) -> bool:
    """Check if a process error might be recoverable with fallback logic."""
    error_str = str(error).lower()
    is_not_found = "404" in str(error) or "not found" in error_str
    is_bad_request = "400" in str(error) or "bad request" in error_str
    is_zero_uuid = process_id == "00000000-0000-0000-0000-000000000000"
    
    return is_not_found or (is_bad_request and not is_zero_uuid)