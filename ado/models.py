from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from enum import Enum

class Project(BaseModel):
    """
    Represents an Azure DevOps project.
    """
    id: str
    name: str
    description: Optional[str] = None
    url: str
    state: str
    revision: int
    visibility: str
    lastUpdateTime: str

class ConfigurationType(str, Enum):
    """
    Configuration types for Azure DevOps pipelines.
    """
    YAML = "yaml"
    DESIGNER_JSON = "designerJson"
    JUST_IN_TIME = "justInTime"
    DESIGNER_HYPHEN_JSON = "designerHyphenJson"
    UNKNOWN = "unknown"

class ServiceConnection(BaseModel):
    """
    Represents a service connection.
    """
    id: str

class Repository(BaseModel):
    """
    Represents a repository configuration for pipelines.
    """
    fullName: str
    connection: ServiceConnection
    type: str

class PipelineConfiguration(BaseModel):
    """
    Represents pipeline configuration.
    """
    type: ConfigurationType
    path: Optional[str] = None
    repository: Optional[Repository] = None

class ReferenceLinks(BaseModel):
    """
    Represents reference links for ADO objects.
    """
    links: Optional[Dict[str, Any]] = None

class Pipeline(BaseModel):
    """
    Represents an Azure DevOps pipeline.
    """
    id: int
    name: str
    revision: int
    url: str
    folder: Optional[str] = None
    configuration: Optional[PipelineConfiguration] = None
    links: Optional[ReferenceLinks] = Field(None, alias="_links")

    model_config = {"populate_by_name": True}

class CreatePipelineRequest(BaseModel):
    """
    Request model for creating a new pipeline.
    """
    name: str
    folder: Optional[str] = None
    configuration: PipelineConfiguration

class PipelineRun(BaseModel):
    """
    Represents a pipeline run.
    """
    id: int
    name: Optional[str] = None
    url: str
    state: Optional[str] = None
    result: Optional[str] = None
    createdDate: Optional[str] = None
    finishedDate: Optional[str] = None