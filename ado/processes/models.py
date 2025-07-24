"""Data models for Azure DevOps processes and templates."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Process(BaseModel):
    """
    Represents a process template in Azure DevOps.

    A process defines the work item types, states, fields, and rules
    that are available in projects that use this process template.
    """

    id: str = Field(..., description="Process unique identifier (UUID)")
    name: str = Field(..., description="Process name (e.g., 'Agile', 'Scrum')")
    description: str | None = Field(None, description="Process description")
    type: str | None = Field(None, description="Process type (system, custom, inherited)")
    isDefault: bool | None = Field(None, description="Whether this is the default process")
    isEnabled: bool | None = Field(None, description="Whether the process is enabled")
    customizationType: str | None = Field(None, description="Customization type")
    parentProcessTypeId: str | None = Field(None, description="Parent process type ID")
    url: str | None = Field(None, description="API URL for the process")
    links: dict[str, Any] | None = Field(None, description="Reference links", alias="_links")


class ProcessTemplate(BaseModel):
    """
    Represents a process template reference.

    Process templates are the blueprints that define work item types,
    workflow states, and rules for projects.
    """

    id: str = Field(..., description="Template unique identifier")
    name: str = Field(..., description="Template name")
    description: str | None = Field(None, description="Template description")
    type: str | None = Field(None, description="Template type")
    url: str | None = Field(None, description="API URL")
    links: dict[str, Any] | None = Field(None, description="Reference links", alias="_links")


class WorkItemTemplate(BaseModel):
    """
    Represents a work item template.

    Work item templates contain predefined field values that can be
    applied when creating new work items to save time and ensure consistency.
    """

    id: str = Field(..., description="Template unique identifier")
    name: str = Field(..., description="Template name")
    description: str | None = Field(None, description="Template description")
    workItemTypeName: str = Field(..., description="Associated work item type")
    fields: dict[str, Any] = Field(default_factory=dict, description="Predefined field values")
    url: str | None = Field(None, description="API URL")
    links: dict[str, Any] | None = Field(None, description="Reference links", alias="_links")


class ProjectProcessInfo(BaseModel):
    """
    Represents process information for a project.

    Contains the process template configuration details for a specific project,
    including the current process and any process history.
    """

    projectId: str = Field(..., description="Project unique identifier")
    currentProcessTemplateId: str = Field(..., description="Current process template ID")
    originalProcessTemplateId: str | None = Field(None, description="Original process template ID")
    processTemplateName: str | None = Field(None, description="Process template name")
    processTemplateType: str | None = Field(None, description="Process template type")

    model_config = ConfigDict(extra="allow")


class TeamInfo(BaseModel):
    """
    Represents basic team information needed for template operations.

    Teams are required context for work item template operations.
    """

    id: str = Field(..., description="Team unique identifier")
    name: str = Field(..., description="Team name")
    description: str | None = Field(None, description="Team description")
    url: str | None = Field(None, description="API URL")
    projectId: str | None = Field(None, description="Associated project ID")
    projectName: str | None = Field(None, description="Associated project name")
