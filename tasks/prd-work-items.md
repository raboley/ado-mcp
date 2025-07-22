# Product Requirements Document: Azure DevOps Work Items Feature

## Introduction

This feature enables users to create, read, update, delete, and query work items in Azure DevOps through the MCP server. Work items are the primary units for tracking work in Azure DevOps, including user stories, tasks, bugs, features, and epics. This integration will allow automation tools and bots to programmatically manage work items as part of their workflows.

## Goals

- Enable full CRUD operations on Azure DevOps work items through MCP tools
- Support all standard work item types (Epic, Feature, User Story, Task, Bug, etc.)
- Provide querying capabilities to find and filter work items
- Allow bulk operations for efficiency
- Support work item relationships and hierarchies
- Enable comment and history tracking on work items
- Maintain consistency with existing MCP server authentication patterns

## User Stories

### Primary User Stories

3. **As an automation tool**, I want to query work items by various criteria, so that I can find relevant items for processing.

4. **As an automation tool**, I want to add comments to work items, so that automated actions are documented.

5. **As an automation tool**, I want to link work items together, so that relationships between items are maintained.

### Secondary User Stories

6. **As an automation tool**, I want to bulk update multiple work items, so that I can efficiently process many items at once.

7. **As an automation tool**, I want to read work item history, so that I can understand how items have changed over time.

8. **As an automation tool**, I want to delete work items when appropriate, so that invalid or duplicate items can be removed.

## Functional Requirements

1. **List Work Item Types**
   - The system must provide a tool to list all available work item types for a given project
   - Must return type names, descriptions, and available fields for each type

2. **Create Work Item**
   - The system must allow creating work items of any available type
   - Must accept a dictionary of fields since fields vary by type and project
   - Must support JSON Patch format as required by Azure DevOps API
   - Must validate required fields before submission
   - Must handle area and iteration paths

3. **Get Work Item**
   - The system must retrieve single work items by ID
   - Must support batch retrieval of multiple work items
   - Must return all fields or specified fields only
   - Must include option to expand related items

4. **Update Work Item**
   - The system must update existing work items using JSON Patch operations
   - Must support add, remove, and replace operations on fields
   - Must handle optimistic concurrency with proper conflict resolution
   - Must support updating multiple fields in a single operation

5. **Delete Work Item**
   - The system must support soft delete (move to recycle bin)
   - Must support permanent deletion when requested
   - Must handle batch deletion of multiple items

6. **Query Work Items**
   - The system must support either simple filtering or WIQL queries (whichever is easier to implement)
   - Must return paginated results for large result sets
   - Must support common queries like "assigned to me", "created by me", "recent items"

7. **Work Item Comments**
   - The system must support adding comments to work items
   - Must retrieve comment history with authors and timestamps
   - Must support formatting in comments (HTML/Markdown)

8. **Work Item History**
   - The system must retrieve revision history for work items
   - Must show what changed, when, and by whom
   - Must support filtering history by date range

9. **Work Item Relationships**
   - The system must support creating parent/child relationships
   - Must support related item links
   - Must handle relationship types (blocks, tests, etc.)

10. **Bulk Operations**
    - The system must support updating multiple work items in a single call
    - Must provide transaction-like behavior (all succeed or all fail)
    - Must return detailed results for each item

11. **Field Validation**
    - The system must provide detailed field-level validation errors
    - Must indicate which fields are required vs optional
    - Must validate field values against allowed values

12. **Area and Iteration Paths**
    - The system must support specifying area and iteration paths when creating/updating items
    - Must provide tools to list available paths in a project
    - Must validate paths exist before assignment

## Non-Goals

- Work item templates management (future enhancement)
- Work item attachments/file uploads (future enhancement)
- Custom field definitions (use existing fields only)
- Work item type creation or modification
- Process template modifications
- Board/backlog visualization features
- Real-time notifications or webhooks
- Work item tags management (future enhancement)

## Design Considerations

### Tool Organization
Tools should be organized into logical groups:
- Basic CRUD: `create_work_item`, `get_work_item`, `update_work_item`, `delete_work_item`
- Batch operations: `get_work_items_batch`, `update_work_items_batch`, `delete_work_items_batch`
- Queries: `query_work_items`, `get_my_work_items`, `get_recent_work_items`
- Comments: `add_work_item_comment`, `get_work_item_comments`
- History: `get_work_item_history`, `get_work_item_revisions`
- Relationships: `link_work_items`, `get_work_item_relations`
- Metadata: `list_work_item_types`, `get_work_item_type_fields`, `list_area_paths`, `list_iteration_paths`

### Field Handling
Since fields vary by project and work item type, use a dictionary approach:
```python
fields = {
    "System.Title": "Fix login bug",
    "System.Description": "Users cannot login with SSO",
    "System.AreaPath": "MyProject\\Web",
    "System.IterationPath": "MyProject\\Sprint 1",
    "System.AssignedTo": "user@example.com"
}
```

### Error Messages
Provide clear, actionable error messages:
- "Field 'System.Title' is required for work item type 'Bug'"
- "Area path 'MyProject\\InvalidArea' does not exist"
- "Work item 12345 was modified by another user. Please refresh and retry."

## Technical Considerations

### Authentication
- Use the same PAT (Personal Access Token) authentication as existing pipeline tools
- Token must have Work Items (Read, Write, & Manage) permissions

### API Integration
- Use Azure DevOps REST API v7.1 or later
- Implement proper retry logic with exponential backoff
- Handle rate limiting gracefully
- Use batch APIs where available for performance

### Caching Strategy
- Cache work item types per project (TTL: 1 hour)
- Cache area/iteration paths per project (TTL: 1 hour)
- Do not cache work item data itself (always fetch latest)
- Use existing cache implementation from pipeline tools

### Performance
- Batch operations should process up to 200 items (API limit)
- Implement pagination for query results
- Use field filtering to reduce payload size
- Implement connection pooling for API requests

### Dependencies
New models needed:
- WorkItem
- WorkItemType
- WorkItemField
- WorkItemComment
- WorkItemRevision
- WorkItemRelation
- WorkItemQueryResult

Existing dependencies:
- AdoClient for API communication
- Authentication from existing implementation
- Caching infrastructure
- Error handling patterns

### Related Azure DevOps APIs
Required endpoints (base URL: `https://dev.azure.com/{organization}/{project}/_apis/wit/`):
- `/workitemtypes` - List work item types
- `/workitems/${id}` - Get/Update/Delete work item
- `/workitems/${type}` - Create work item
- `/workitems` - Batch operations
- `/wiql` - Work item queries
- `/workitems/${id}/comments` - Comments
- `/workitems/${id}/revisions` - History
- `/classificationnodes` - Area/Iteration paths

Documentation references:
- [Work Items REST API](https://learn.microsoft.com/en-us/rest/api/azure/devops/wit/work-items?view=azure-devops-rest-7.1)
- [Work Item Types API](https://learn.microsoft.com/en-us/rest/api/azure/devops/wit/work-item-types?view=azure-devops-rest-7.1)
- [WIQL Syntax](https://learn.microsoft.com/en-us/azure/devops/boards/queries/wiql-syntax?view=azure-devops)
- [Classification Nodes API](https://learn.microsoft.com/en-us/rest/api/azure/devops/wit/classification-nodes?view=azure-devops-rest-7.1)

## Success Metrics

- Successfully create work items of all standard types
- Update work items without conflicts in 95% of cases
- Query performance returns results in under 2 seconds for typical queries
- Bulk operations process 100+ items successfully
- Zero data loss or corruption incidents
- Comment and history retrieval works reliably
- Proper error messages help users resolve issues quickly

## Open Questions

1. Should we implement WIQL query support or start with simpler filtering? (Decision: Start with whichever is easier)
2. What is the maximum number of work items we should support in batch operations? (100)
4. Do we need to support custom fields beyond the standard Azure DevOps fields? Not unless it is just a basic dictionary of fields.
5. Should we implement work item state transition validation? yes, when we try to do something we need to validate it happens.
6. How should we handle work items in different projects when doing cross-project queries? (future enhancement)
7. Should deleted work items be automatically purged after a certain time? leave it to default.