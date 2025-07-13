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

class RunState(str, Enum):
    """
    Represents the state of a pipeline run.
    """
    UNKNOWN = "unknown"
    IN_PROGRESS = "inProgress"
    COMPLETED = "completed"
    CANCELING = "canceling"

class RunResult(str, Enum):
    """
    Represents the result of a pipeline run.
    """
    UNKNOWN = "unknown"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"

class PipelineReference(BaseModel):
    """
    Represents a reference to a pipeline.
    """
    id: int
    name: Optional[str] = None
    url: Optional[str] = None
    folder: Optional[str] = None

class PipelineRun(BaseModel):
    """
    Represents a pipeline run with comprehensive status tracking.
    """
    id: int
    name: Optional[str] = None
    url: str
    state: Optional[RunState] = None
    result: Optional[RunResult] = None
    createdDate: Optional[str] = None
    finishedDate: Optional[str] = None
    pipeline: Optional[PipelineReference] = None
    resources: Optional[Dict[str, Any]] = None
    variables: Optional[Dict[str, Any]] = None

    def is_completed(self) -> bool:
        """
        Check if the pipeline run has completed.
        
        Returns:
            bool: True if the run is completed, False otherwise.
        """
        return self.state == RunState.COMPLETED

    def is_successful(self) -> bool:
        """
        Check if the pipeline run completed successfully.
        
        Returns:
            bool: True if the run succeeded, False otherwise.
        """
        return self.is_completed() and self.result == RunResult.SUCCEEDED

    def is_failed(self) -> bool:
        """
        Check if the pipeline run failed.
        
        Returns:
            bool: True if the run failed, False otherwise.
        """
        return self.is_completed() and self.result == RunResult.FAILED

    def is_in_progress(self) -> bool:
        """
        Check if the pipeline run is currently in progress.
        
        Returns:
            bool: True if the run is in progress, False otherwise.
        """
        return self.state == RunState.IN_PROGRESS