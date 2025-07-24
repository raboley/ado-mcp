"""Data models for Azure DevOps Work Items."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class JsonPatchOperation(BaseModel):
    """Represents a single JSON Patch operation."""

    op: str = Field(..., description="The operation type: add, remove, replace, move, copy, test")
    path: str = Field(..., description="The JSON path to the target location")
    value: Any | None = Field(None, description="The value to be used in the operation")
    from_: str | None = Field(
        None, alias="from", description="The source path for move/copy operations"
    )


class JsonPatchDocument(BaseModel):
    """Represents a JSON Patch document containing multiple operations."""

    operations: list[JsonPatchOperation] = Field(..., description="List of patch operations")


class WorkItemField(BaseModel):
    """Represents a field in a work item type."""

    referenceName: str
    name: str
    type: str | None = None
    readOnly: bool | None = None
    required: bool | None = None
    alwaysRequired: bool | None = None
    allowedValues: list[Any] | None = None
    defaultValue: Any | None = None
    helpText: str | None = None
    url: str | None = None


class WorkItemTypeState(BaseModel):
    """Represents a state in a work item type."""

    name: str = Field(..., description="The name of the state")
    color: str | None = Field(None, description="Color associated with the state")
    category: str | None = Field(
        None, description="Category of the state (Proposed, InProgress, Completed)"
    )


class WorkItemTypeTransition(BaseModel):
    """Represents a state transition in a work item type."""

    to: str = Field(..., description="The target state name")
    actions: list[str] | None = Field(None, description="Actions available during this transition")


class WorkItemType(BaseModel):
    """Represents a work item type in Azure DevOps."""

    name: str
    referenceName: str
    description: str | None = None
    color: str | None = None
    icon: dict[str, Any] | None = None
    isDisabled: bool | None = None
    xmlForm: str | None = None
    url: str | None = None
    # Note: fields, states, and transitions are complex nested objects that vary by API call
    # They're not always present in list_work_item_types response
    fields: list[dict[str, Any]] | None = None
    states: list[dict[str, Any]] | None = None
    transitions: dict[str, list[dict[str, Any]]] | None = None


class WorkItem(BaseModel):
    """Represents a work item in Azure DevOps."""

    id: int | None = Field(None, description="The work item ID")
    rev: int | None = Field(None, description="The revision number")
    fields: dict[str, Any] = Field(..., description="Work item fields as key-value pairs")
    relations: list["WorkItemRelation"] | None = Field(None, description="Related work items")
    url: str | None = Field(None, description="The REST URL of the work item")
    links: dict[str, Any] | None = Field(None, alias="_links", description="Hypermedia links")


class WorkItemRelationType(str, Enum):
    """Types of relationships between work items."""

    PARENT = "System.LinkTypes.Hierarchy-Reverse"
    CHILD = "System.LinkTypes.Hierarchy-Forward"
    RELATED = "System.LinkTypes.Related"
    DUPLICATE = "System.LinkTypes.Duplicate"
    DUPLICATE_OF = "System.LinkTypes.Duplicate-Reverse"
    SUCCESSOR = "System.LinkTypes.Dependency-Forward"
    PREDECESSOR = "System.LinkTypes.Dependency-Reverse"
    BLOCKS = "Microsoft.VSTS.Common.Affects-Forward"
    BLOCKED_BY = "Microsoft.VSTS.Common.Affects-Reverse"
    TESTS = "Microsoft.VSTS.Common.TestedBy-Forward"
    TESTED_BY = "Microsoft.VSTS.Common.TestedBy-Reverse"


class WorkItemRelation(BaseModel):
    """Represents a relationship between work items."""

    rel: str = Field(..., description="The relationship type")
    url: str = Field(..., description="The URL of the related work item")
    attributes: dict[str, Any] | None = Field(
        None, description="Additional attributes of the relation"
    )


class WorkItemComment(BaseModel):
    """Represents a comment on a work item."""

    id: int | None = Field(None, description="The comment ID")
    work_item_id: int = Field(..., description="The ID of the work item")
    text: str = Field(..., description="The comment text (supports HTML/Markdown)")
    created_by: dict[str, Any] | None = Field(None, description="User who created the comment")
    created_date: datetime | None = Field(None, description="When the comment was created")
    modified_by: dict[str, Any] | None = Field(
        None, description="User who last modified the comment"
    )
    modified_date: datetime | None = Field(None, description="When the comment was last modified")
    format: str | None = Field("html", description="The format of the comment text")


class WorkItemRevision(BaseModel):
    """Represents a revision in work item history."""

    id: int = Field(..., description="The work item ID")
    rev: int = Field(..., description="The revision number")
    fields: dict[str, Any] = Field(..., description="Fields at this revision")
    url: str | None = Field(None, description="The REST URL of this revision")
    revised_by: dict[str, Any] | None = Field(None, description="User who made this revision")
    revised_date: datetime | None = Field(None, description="When this revision was made")


class WorkItemReference(BaseModel):
    """Represents a reference to a work item from query results."""

    id: int = Field(..., description="The work item ID")
    url: str = Field(..., description="The REST URL of the work item")


class WorkItemQueryResult(BaseModel):
    """Represents the result of a work item query."""

    queryType: str = Field(..., description="The type of query (flat, tree, oneHop)")
    queryResultType: str | None = Field(
        None, description="The type of results (workItem, workItemLink)"
    )
    asOf: str | None = Field(None, description="The date/time the query was run")
    workItems: list[WorkItemReference] = Field(
        ..., description="The work items returned by the query"
    )
    columns: list[dict[str, Any]] | None = Field(None, description="Column information")
    sortColumns: list[dict[str, Any]] | None = Field(None, description="Sort column information")


class ClassificationNode(BaseModel):
    """Represents a classification node (area path or iteration path)."""

    id: int | None = None
    name: str | None = None
    path: str | None = None
    url: str | None = None
    structureType: str | None = None
    hasChildren: bool | None = None
    children: list["ClassificationNode"] | None = None
    attributes: dict[str, Any] | None = None


# Update forward references
WorkItem.model_rebuild()
WorkItemType.model_rebuild()
ClassificationNode.model_rebuild()
