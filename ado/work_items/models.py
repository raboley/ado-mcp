"""Data models for Azure DevOps Work Items."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class JsonPatchOperation(BaseModel):
    """Represents a single JSON Patch operation."""
    
    op: str = Field(..., description="The operation type: add, remove, replace, move, copy, test")
    path: str = Field(..., description="The JSON path to the target location")
    value: Optional[Any] = Field(None, description="The value to be used in the operation")
    from_: Optional[str] = Field(None, alias="from", description="The source path for move/copy operations")


class JsonPatchDocument(BaseModel):
    """Represents a JSON Patch document containing multiple operations."""
    
    operations: List[JsonPatchOperation] = Field(..., description="List of patch operations")


class WorkItemField(BaseModel):
    """Represents a field in a work item type."""
    
    referenceName: str
    name: str
    type: Optional[str] = None
    readOnly: Optional[bool] = None
    required: Optional[bool] = None
    alwaysRequired: Optional[bool] = None
    allowedValues: Optional[List[Any]] = None
    defaultValue: Optional[Any] = None
    helpText: Optional[str] = None
    url: Optional[str] = None


class WorkItemTypeState(BaseModel):
    """Represents a state in a work item type."""
    
    name: str = Field(..., description="The name of the state")
    color: Optional[str] = Field(None, description="Color associated with the state")
    category: Optional[str] = Field(None, description="Category of the state (Proposed, InProgress, Completed)")


class WorkItemTypeTransition(BaseModel):
    """Represents a state transition in a work item type."""
    
    to: str = Field(..., description="The target state name")
    actions: Optional[List[str]] = Field(None, description="Actions available during this transition")


class WorkItemType(BaseModel):
    """Represents a work item type in Azure DevOps."""
    
    name: str
    referenceName: str
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[Dict[str, Any]] = None
    isDisabled: Optional[bool] = None
    xmlForm: Optional[str] = None
    url: Optional[str] = None
    # Note: fields, states, and transitions are complex nested objects that vary by API call
    # They're not always present in list_work_item_types response
    fields: Optional[List[Dict[str, Any]]] = None
    states: Optional[List[Dict[str, Any]]] = None
    transitions: Optional[Dict[str, List[Dict[str, Any]]]] = None


class WorkItem(BaseModel):
    """Represents a work item in Azure DevOps."""
    
    id: Optional[int] = Field(None, description="The work item ID")
    rev: Optional[int] = Field(None, description="The revision number")
    fields: Dict[str, Any] = Field(..., description="Work item fields as key-value pairs")
    relations: Optional[List["WorkItemRelation"]] = Field(None, description="Related work items")
    url: Optional[str] = Field(None, description="The REST URL of the work item")
    links: Optional[Dict[str, Any]] = Field(None, alias="_links", description="Hypermedia links")


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
    attributes: Optional[Dict[str, Any]] = Field(None, description="Additional attributes of the relation")


class WorkItemComment(BaseModel):
    """Represents a comment on a work item."""
    
    id: Optional[int] = Field(None, description="The comment ID")
    work_item_id: int = Field(..., description="The ID of the work item")
    text: str = Field(..., description="The comment text (supports HTML/Markdown)")
    created_by: Optional[Dict[str, Any]] = Field(None, description="User who created the comment")
    created_date: Optional[datetime] = Field(None, description="When the comment was created")
    modified_by: Optional[Dict[str, Any]] = Field(None, description="User who last modified the comment")
    modified_date: Optional[datetime] = Field(None, description="When the comment was last modified")
    format: Optional[str] = Field("html", description="The format of the comment text")


class WorkItemRevision(BaseModel):
    """Represents a revision in work item history."""
    
    id: int = Field(..., description="The work item ID")
    rev: int = Field(..., description="The revision number")
    fields: Dict[str, Any] = Field(..., description="Fields at this revision")
    url: Optional[str] = Field(None, description="The REST URL of this revision")
    revised_by: Optional[Dict[str, Any]] = Field(None, description="User who made this revision")
    revised_date: Optional[datetime] = Field(None, description="When this revision was made")
    
    
class WorkItemQueryResult(BaseModel):
    """Represents the result of a work item query."""
    
    query_type: str = Field(..., description="The type of query (flat, tree, oneHop)")
    query_result_type: str = Field(..., description="The type of results (workItem, workItemLink)")
    as_of: Optional[datetime] = Field(None, description="The date/time the query was run")
    work_items: List[WorkItem] = Field(..., description="The work items returned by the query")
    columns: Optional[List[str]] = Field(None, description="Column names in the result")
    sort_columns: Optional[List[Dict[str, Any]]] = Field(None, description="Sort column information")


class ClassificationNode(BaseModel):
    """Represents a classification node (area path or iteration path)."""
    
    id: Optional[int] = None
    name: Optional[str] = None
    path: Optional[str] = None
    url: Optional[str] = None
    structureType: Optional[str] = None
    hasChildren: Optional[bool] = None
    children: Optional[List["ClassificationNode"]] = None
    attributes: Optional[Dict[str, Any]] = None


# Update forward references
WorkItem.model_rebuild()
WorkItemType.model_rebuild()
ClassificationNode.model_rebuild()