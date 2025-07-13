from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
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


class PipelinePreviewRequest(BaseModel):
    """
    Request model for previewing a pipeline without executing it.
    """
    previewRun: Optional[bool] = True
    yamlOverride: Optional[str] = None
    resources: Optional[Dict[str, Any]] = None
    templateParameters: Optional[Dict[str, Any]] = None
    variables: Optional[Dict[str, Any]] = None
    stagesToSkip: Optional[List[str]] = None


class PreviewRun(BaseModel):
    """
    Represents the result of a pipeline preview operation.
    """
    finalYaml: Optional[str] = None
    id: Optional[int] = None
    name: Optional[str] = None
    url: Optional[str] = None
    resources: Optional[Dict[str, Any]] = None
    variables: Optional[Dict[str, Any]] = None
    pipeline: Optional[PipelineReference] = None


class TimelineRecord(BaseModel):
    """
    Represents a single record in the build timeline (stage, job, task, etc.).
    """
    id: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None  # Stage, Job, Phase, Task, Checkpoint
    state: Optional[str] = None  # completed, inProgress
    result: Optional[str] = None  # succeeded, failed, skipped
    startTime: Optional[str] = None
    finishTime: Optional[str] = None
    log: Optional[Dict[str, Any]] = None  # Contains log ID reference
    task: Optional[Dict[str, Any]] = None  # Contains task information
    issues: Optional[List[Dict[str, Any]]] = None  # Contains error/warning messages
    parentId: Optional[str] = None


class TimelineResponse(BaseModel):
    """
    Represents the response from the build timeline API.
    """
    records: List[TimelineRecord]
    lastChangedBy: Optional[str] = None  # Can be either string (user ID) or dict (user object)
    lastChangedOn: Optional[str] = None
    id: Optional[str] = None
    changeId: Optional[int] = None
    url: Optional[str] = None


class StepFailure(BaseModel):
    """
    Represents a failed step with its details and log content.
    """
    step_name: str
    step_type: str  # Task, Job, Stage, Phase
    result: str     # failed, succeeded, skipped
    log_id: Optional[int] = None
    issues: List[str] = []
    log_content: Optional[str] = None
    start_time: Optional[str] = None
    finish_time: Optional[str] = None


class FailureSummary(BaseModel):
    """
    Represents a comprehensive summary of pipeline failures.
    """
    total_failed_steps: int
    root_cause_tasks: List[StepFailure]  # Only Task-level failures (root causes)
    hierarchy_failures: List[StepFailure]  # Job/Stage level that failed due to tasks
    pipeline_url: Optional[str] = None
    build_id: Optional[int] = None


class LogEntry(BaseModel):
    """
    Represents a single log entry from the logs API.
    """
    id: int
    createdOn: str
    lastChangedOn: str
    lineCount: int
    url: str
    signedContent: Optional[Dict[str, Any]] = None


class LogCollection(BaseModel):
    """
    Represents the collection of logs for a pipeline run.
    """
    logs: List[LogEntry]
    url: str