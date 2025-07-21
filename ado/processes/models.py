"""Data models for Azure DevOps processes and templates."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Process(BaseModel):
    """
    Represents a process template in Azure DevOps.
    
    A process defines the work item types, states, fields, and rules
    that are available in projects that use this process template.
    """
    id: str = Field(..., description="Process unique identifier (UUID)")
    name: str = Field(..., description="Process name (e.g., 'Agile', 'Scrum')")
    description: Optional[str] = Field(None, description="Process description")
    type: Optional[str] = Field(None, description="Process type (system, custom, inherited)")
    isDefault: Optional[bool] = Field(None, description="Whether this is the default process")
    isEnabled: Optional[bool] = Field(None, description="Whether the process is enabled")
    customizationType: Optional[str] = Field(None, description="Customization type")
    parentProcessTypeId: Optional[str] = Field(None, description="Parent process type ID")
    url: Optional[str] = Field(None, description="API URL for the process")
    links: Optional[Dict[str, Any]] = Field(None, description="Reference links", alias="_links")


class ProcessTemplate(BaseModel):
    """
    Represents a process template reference.
    
    Process templates are the blueprints that define work item types,
    workflow states, and rules for projects.
    """
    id: str = Field(..., description="Template unique identifier")
    name: str = Field(..., description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    type: Optional[str] = Field(None, description="Template type")
    url: Optional[str] = Field(None, description="API URL")
    links: Optional[Dict[str, Any]] = Field(None, description="Reference links", alias="_links")


class WorkItemTemplate(BaseModel):
    """
    Represents a work item template.
    
    Work item templates contain predefined field values that can be
    applied when creating new work items to save time and ensure consistency.
    """
    id: str = Field(..., description="Template unique identifier")
    name: str = Field(..., description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    workItemTypeName: str = Field(..., description="Associated work item type")
    fields: Dict[str, Any] = Field(default_factory=dict, description="Predefined field values")
    url: Optional[str] = Field(None, description="API URL")
    links: Optional[Dict[str, Any]] = Field(None, description="Reference links", alias="_links")


class ProjectProcessInfo(BaseModel):
    """
    Represents process information for a project.
    
    Contains the process template configuration details for a specific project,
    including the current process and any process history.
    """
    projectId: str = Field(..., description="Project unique identifier")
    currentProcessTemplateId: str = Field(..., description="Current process template ID")
    originalProcessTemplateId: Optional[str] = Field(None, description="Original process template ID")
    processTemplateName: Optional[str] = Field(None, description="Process template name")
    processTemplateType: Optional[str] = Field(None, description="Process template type")
    
    class Config:
        """Pydantic configuration."""
        extra = "allow"  # Allow additional fields from API response


class TeamInfo(BaseModel):
    """
    Represents basic team information needed for template operations.
    
    Teams are required context for work item template operations.
    """
    id: str = Field(..., description="Team unique identifier")
    name: str = Field(..., description="Team name")
    description: Optional[str] = Field(None, description="Team description")
    url: Optional[str] = Field(None, description="API URL")
    projectId: Optional[str] = Field(None, description="Associated project ID")
    projectName: Optional[str] = Field(None, description="Associated project name")