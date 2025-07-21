"""MCP tools for Azure DevOps Processes and Templates."""

import logging
from typing import List, Optional

from ado.processes.client import ProcessesClient
from ado.processes.models import Process, WorkItemTemplate, ProjectProcessInfo

logger = logging.getLogger(__name__)


def register_process_tools(mcp_instance, client_container):
    """
    Register all process and template tools with the MCP server.
    
    Args:
        mcp_instance: The MCP server instance
        client_container: Container holding the ADO client
    """
    
    @mcp_instance.tool
    def get_project_process_id(project_id: str) -> Optional[str]:
        """
        Get the process template ID for a project.
        
        Every Azure DevOps project is based on a process template that defines
        the work item types, workflow states, and business rules available in
        the project. This tool retrieves the process template ID.
        
        Args:
            project_id: The ID or name of the project.
            
        Returns:
            str: The process template ID (UUID), or None if client unavailable.
            
        Examples:
            # Get process ID for a project
            get_project_process_id(project_id="MyProject")
            
            # Result might be something like:
            # "adcc42ab-9882-485e-a3ed-7678f01f66bc"
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None
            
        try:
            processes_client = ProcessesClient(ado_client_instance)
            process_id = processes_client.get_project_process_id(project_id)
            
            logger.info(f"Successfully retrieved process ID for project '{project_id}': {process_id}")
            return process_id
            
        except Exception as e:
            logger.error(f"Failed to get process ID for project '{project_id}': {e}")
            raise

    @mcp_instance.tool  
    def get_project_process_info(project_id: str) -> Optional[ProjectProcessInfo]:
        """
        Get comprehensive process information for a project.
        
        This tool provides detailed information about the process template
        configuration for a project, including current and original process
        template details.
        
        Args:
            project_id: The ID or name of the project.
            
        Returns:
            ProjectProcessInfo: Complete process information, or None if client unavailable.
            
        Examples:
            # Get comprehensive process info
            get_project_process_info(project_id="MyProject")
            
            # Returns information about:
            # - Current process template ID
            # - Process template name (e.g., "Agile", "Scrum") 
            # - Original process template ID
            # - Process template type
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None
            
        try:
            processes_client = ProcessesClient(ado_client_instance)
            process_info = processes_client.get_project_process_info(project_id)
            
            logger.info(f"Successfully retrieved process info for project '{project_id}': {process_info.processTemplateName}")
            return process_info
            
        except Exception as e:
            logger.error(f"Failed to get process info for project '{project_id}': {e}")
            raise

    @mcp_instance.tool
    def list_processes() -> Optional[List[Process]]:
        """
        List all available process templates in the organization.
        
        Process templates define the work item types, states, fields, and rules
        that are available in projects. This tool lists all process templates
        that can be used when creating new projects.
        
        Returns:
            List[Process]: List of available processes, or None if client unavailable.
            
        Examples:
            # List all available processes
            list_processes()
            
            # Typical results include:
            # - Agile: Flexible template for Agile development
            # - Scrum: Template for Scrum methodology  
            # - CMMI: Capability Maturity Model Integration template
            # - Basic: Simple template with basic work item types
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None
            
        try:
            processes_client = ProcessesClient(ado_client_instance)
            processes = processes_client.list_processes()
            
            logger.info(f"Successfully retrieved {len(processes)} processes")
            return processes
            
        except Exception as e:
            logger.error(f"Failed to list processes: {e}")
            raise

    @mcp_instance.tool
    def get_process_details(process_id: str) -> Optional[Process]:
        """
        Get detailed information about a specific process template.
        
        This tool provides comprehensive details about a process template,
        including its configuration, customization type, and relationship
        to other processes.
        
        Args:
            process_id: The process template ID (UUID).
            
        Returns:
            Process: Detailed process information, or None if client unavailable.
            
        Examples:
            # Get details for a specific process
            get_process_details(process_id="adcc42ab-9882-485e-a3ed-7678f01f66bc")
            
            # Returns detailed information including:
            # - Process name and description
            # - Whether it's a system, custom, or inherited process
            # - Default status and enabled state
            # - Parent process (for inherited processes)
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None
            
        try:
            processes_client = ProcessesClient(ado_client_instance)
            process = processes_client.get_process_details(process_id)
            
            logger.info(f"Successfully retrieved process details for '{process.name}' ({process_id})")
            return process
            
        except Exception as e:
            logger.error(f"Failed to get process details for process '{process_id}': {e}")
            raise

    @mcp_instance.tool
    def get_work_item_templates(
        project_id: str,
        team_id: Optional[str] = None,
        work_item_type: Optional[str] = None
    ) -> Optional[List[WorkItemTemplate]]:
        """
        Get work item templates for a team.
        
        Work item templates contain predefined field values that can be applied
        when creating new work items. They help ensure consistency and save time
        by providing commonly used configurations.
        
        Args:
            project_id: The ID or name of the project.
            team_id: The team ID. If not provided, uses the project's default team.
            work_item_type: Optional filter to only return templates for a specific
                          work item type (e.g., "Bug", "User Story", "Task").
                          
        Returns:
            List[WorkItemTemplate]: List of available templates, or None if client unavailable.
            
        Examples:
            # Get all templates for a project's default team
            get_work_item_templates(project_id="MyProject")
            
            # Get templates for a specific team
            get_work_item_templates(
                project_id="MyProject",
                team_id="team-uuid-here"
            )
            
            # Get only Bug templates
            get_work_item_templates(
                project_id="MyProject", 
                work_item_type="Bug"
            )
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None
            
        try:
            processes_client = ProcessesClient(ado_client_instance)
            templates = processes_client.get_work_item_templates(
                project_id=project_id,
                team_id=team_id,
                work_item_type=work_item_type
            )
            
            logger.info(f"Successfully retrieved {len(templates)} work item templates")
            return templates
            
        except Exception as e:
            logger.error(f"Failed to get work item templates: {e}")
            raise

    @mcp_instance.tool
    def get_work_item_template(
        project_id: str,
        template_id: str,
        team_id: Optional[str] = None
    ) -> Optional[WorkItemTemplate]:
        """
        Get detailed information about a specific work item template.
        
        This tool provides complete details about a work item template,
        including all predefined field values and configurations.
        
        Args:
            project_id: The ID or name of the project.
            template_id: The template ID (UUID).
            team_id: The team ID. If not provided, uses the project's default team.
            
        Returns:
            WorkItemTemplate: Detailed template information, or None if client unavailable.
            
        Examples:
            # Get details for a specific template
            get_work_item_template(
                project_id="MyProject",
                template_id="template-uuid-here"
            )
            
            # Get template details for a specific team
            get_work_item_template(
                project_id="MyProject",
                template_id="template-uuid-here", 
                team_id="team-uuid-here"
            )
        """
        ado_client_instance = client_container.get("client")
        if not ado_client_instance:
            logger.error("ADO client is not available.")
            return None
            
        try:
            processes_client = ProcessesClient(ado_client_instance)
            template = processes_client.get_work_item_template(
                project_id=project_id,
                template_id=template_id,
                team_id=team_id
            )
            
            logger.info(f"Successfully retrieved template '{template.name}' ({template_id})")
            return template
            
        except Exception as e:
            logger.error(f"Failed to get work item template '{template_id}': {e}")
            raise