from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class Project(BaseModel):
    """
    Represents an Azure DevOps project.
    """

    id: str
    name: str
    description: str | None = None
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
    path: str | None = None
    repository: Repository | None = None


class ReferenceLinks(BaseModel):
    """
    Represents reference links for ADO objects.
    """

    links: dict[str, Any] | None = None


class Pipeline(BaseModel):
    """
    Represents an Azure DevOps pipeline.
    """

    id: int
    name: str
    revision: int
    url: str
    folder: str | None = None
    configuration: PipelineConfiguration | None = None
    links: ReferenceLinks | None = Field(None, alias="_links")

    model_config = {"populate_by_name": True}


class CreatePipelineRequest(BaseModel):
    """
    Request model for creating a new pipeline.
    """

    name: str
    folder: str | None = None
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
    name: str | None = None
    url: str | None = None
    folder: str | None = None


class PipelineRun(BaseModel):
    """
    Represents a pipeline run with comprehensive status tracking.
    """

    id: int
    name: str | None = None
    url: str
    state: RunState | None = None
    result: RunResult | None = None
    createdDate: str | None = None
    finishedDate: str | None = None
    pipeline: PipelineReference | None = None
    resources: dict[str, Any] | None = None
    variables: dict[str, Any] | None = None

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

    previewRun: bool | None = True
    yamlOverride: str | None = None
    resources: Optional["RunResourcesParameters"] = None
    templateParameters: dict[str, Any] | None = None
    variables: dict[str, Any] | None = None
    stagesToSkip: list[str] | None = None


class PreviewRun(BaseModel):
    """
    Represents the result of a pipeline preview operation.
    """

    finalYaml: str | None = None
    id: int | None = None
    name: str | None = None
    url: str | None = None
    resources: dict[str, Any] | None = None
    variables: dict[str, Any] | None = None
    pipeline: PipelineReference | None = None


class TimelineRecord(BaseModel):
    """
    Represents a single record in the build timeline (stage, job, task, etc.).
    """

    id: str | None = None
    name: str | None = None
    type: str | None = None  # Stage, Job, Phase, Task, Checkpoint
    state: str | None = None  # completed, inProgress
    result: str | None = None  # succeeded, failed, skipped
    startTime: str | None = None
    finishTime: str | None = None
    log: dict[str, Any] | None = None  # Contains log ID reference
    task: dict[str, Any] | None = None  # Contains task information
    issues: list[dict[str, Any]] | None = None  # Contains error/warning messages
    parentId: str | None = None


class TimelineResponse(BaseModel):
    """
    Represents the response from the build timeline API.
    """

    records: list[TimelineRecord]
    lastChangedBy: str | None = None  # Can be either string (user ID) or dict (user object)
    lastChangedOn: str | None = None
    id: str | None = None
    changeId: int | None = None
    url: str | None = None


class StepFailure(BaseModel):
    """
    Represents a failed step with its details and log content.
    """

    step_name: str
    step_type: str  # Task, Job, Stage, Phase
    result: str  # failed, succeeded, skipped
    log_id: int | None = None
    issues: list[str] = []
    log_content: str | None = None
    start_time: str | None = None
    finish_time: str | None = None


class FailureSummary(BaseModel):
    """
    Represents a comprehensive summary of pipeline failures.
    """

    total_failed_steps: int
    root_cause_tasks: list[StepFailure]  # Only Task-level failures (root causes)
    hierarchy_failures: list[StepFailure]  # Job/Stage level that failed due to tasks
    pipeline_url: str | None = None
    build_id: int | None = None


class LogEntry(BaseModel):
    """
    Represents a single log entry from the logs API.
    """

    id: int
    createdOn: str
    lastChangedOn: str
    lineCount: int
    url: str
    signedContent: dict[str, Any] | None = None


class LogCollection(BaseModel):
    """
    Represents the collection of logs for a pipeline run.
    """

    logs: list[LogEntry]
    url: str


# Azure DevOps API Schema Models for Pipeline Run Parameters


class RepositoryResourceParameters(BaseModel):
    """
    Parameters for repository resources as defined by Azure DevOps API.
    """

    refName: str | None = None
    token: str | None = None
    tokenType: str | None = None
    version: str | None = None


class BuildResourceParameters(BaseModel):
    """
    Parameters for build resources as defined by Azure DevOps API.
    """

    version: str | None = None


class ContainerResourceParameters(BaseModel):
    """
    Parameters for container resources as defined by Azure DevOps API.
    """

    version: str | None = None


class PackageResourceParameters(BaseModel):
    """
    Parameters for package resources as defined by Azure DevOps API.
    """

    version: str | None = None


class PipelineResourceParameters(BaseModel):
    """
    Parameters for pipeline resources as defined by Azure DevOps API.
    """

    version: str | None = None


class RunResourcesParameters(BaseModel):
    """
    Complete resources parameters structure as defined by Azure DevOps API.
    """

    repositories: dict[str, RepositoryResourceParameters] | None = None
    builds: dict[str, BuildResourceParameters] | None = None
    containers: dict[str, ContainerResourceParameters] | None = None
    packages: dict[str, PackageResourceParameters] | None = None
    pipelines: dict[str, PipelineResourceParameters] | None = None


class Variable(BaseModel):
    """
    Variable structure as defined by Azure DevOps API.
    """

    value: str
    isSecret: bool | None = None


class PipelineRunRequest(BaseModel):
    """
    Request model for running a pipeline with parameters, variables, and branch selection.
    Matches Azure DevOps API specification.

    Note: The 'branch' parameter is only supported for pipelines that:
    1. Have a 'resources' section defined in their YAML
    2. Use VM-based pools (not server pools)
    3. Are designed to work with repository checkouts

    Server-pool pipelines or simple pipelines without resources may not support branch overrides.
    """

    resources: RunResourcesParameters | None = None
    templateParameters: dict[str, Any] | None = None
    variables: dict[str, Any] | None = None  # Accept any variable format
    stagesToSkip: list[str] | None = None
    branch: str | None = None  # Branch to run the pipeline from (e.g., "refs/heads/main")
    # Only supported for pipelines with resources sections


class PipelineOutcome(BaseModel):
    """
    Represents the complete outcome of running a pipeline and waiting for completion.

    Contains the pipeline run details and, if the pipeline failed, the failure analysis.
    """

    pipeline_run: PipelineRun
    success: bool
    failure_summary: FailureSummary | None = None
    execution_time_seconds: float


class RepositoryInfo(BaseModel):
    """
    Represents repository resource information from a pipeline run.
    """

    name: str  # Repository alias (e.g., "self", "tooling")
    full_name: str | None = None  # e.g., "owner/repo"
    type: str | None = None  # e.g., "gitHub", "azureReposGit"
    ref_name: str | None = None  # e.g., "refs/heads/main"
    version: str | None = None  # Commit SHA or version
    connection_id: str | None = None


class VariableInfo(BaseModel):
    """
    Represents variable information from a pipeline run.
    """

    name: str
    value: str | None = None
    is_secret: bool = False


class PipelineRunExtractionData(BaseModel):
    """
    Represents extracted resources, variables, and parameters from a pipeline run.
    """

    run_id: int
    pipeline_name: str | None = None
    repositories: list[RepositoryInfo] = Field(default_factory=list)
    variables: list[VariableInfo] = Field(default_factory=list)
    template_parameters: dict[str, Any] = Field(default_factory=dict)
    stages_to_skip: list[str] = Field(default_factory=list)
