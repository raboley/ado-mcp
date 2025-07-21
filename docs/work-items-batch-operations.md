# Azure DevOps Work Items - Batch Operations and Query Syntax

This document provides comprehensive information about batch operations and query syntax for Azure DevOps work items in the ADO MCP server.

## Table of Contents

1. [Batch Operations Overview](#batch-operations-overview)
2. [Batch Retrieval (get_work_items_batch)](#batch-retrieval)
3. [Batch Updates (update_work_items_batch)](#batch-updates)
4. [Batch Deletion (delete_work_items_batch)](#batch-deletion)
5. [Query Syntax and WIQL](#query-syntax-and-wiql)
6. [Performance and Limits](#performance-and-limits)
7. [Error Handling](#error-handling)
8. [Best Practices](#best-practices)

## Batch Operations Overview

The ADO MCP server provides three main batch operations for efficient work item management:

- **get_work_items_batch**: Retrieve multiple work items by ID
- **update_work_items_batch**: Update multiple work items with JSON Patch operations
- **delete_work_items_batch**: Delete or destroy multiple work items

All batch operations are designed with:
- **Performance monitoring**: Detailed metrics and timing information
- **Error policies**: Configurable handling of individual item failures
- **Comprehensive logging**: Structured logging for debugging and observability
- **Transaction-like behavior**: Consistent behavior across all items

### Common Limits

All batch operations have a **200 item limit** to prevent API overload and ensure reasonable performance. This aligns with Azure DevOps API best practices.

## Batch Retrieval

### get_work_items_batch

Retrieve multiple work items by their IDs in a single API call.

```python
get_work_items_batch(
    project_id="MyProject",
    work_item_ids=[123, 124, 125],
    fields=["System.Title", "System.State", "System.AssignedTo"],
    expand_relations=False,
    as_of=None,
    error_policy="omit"
)
```

**Parameters:**
- `project_id` (required): Project ID or name
- `work_item_ids` (required): List of work item IDs (max 200)
- `fields` (optional): Specific fields to return (improves performance)
- `expand_relations` (optional): Include related work items
- `as_of` (optional): Historical query at specific date/time (ISO 8601)
- `error_policy`: "omit" (skip invalid IDs) or "fail" (error on any failure)

**Returns:** List of WorkItem objects

**Use Cases:**
- Getting full details after a WIQL query (which returns only IDs)
- Bulk data retrieval for dashboards or reports
- Validation of work item existence

## Batch Updates

### update_work_items_batch

Update multiple work items using JSON Patch operations with transaction-like behavior.

```python
update_work_items_batch(
    project_id="MyProject",
    work_item_updates=[
        {
            "work_item_id": 123,
            "operations": [
                {"op": "replace", "path": "/fields/System.Title", "value": "New Title"},
                {"op": "replace", "path": "/fields/System.AssignedTo", "value": "user@company.com"}
            ]
        },
        {
            "work_item_id": 124,
            "operations": [
                {"op": "replace", "path": "/fields/System.State", "value": "Active"}
            ]
        }
    ],
    validate_only=False,
    bypass_rules=False,
    suppress_notifications=False,
    error_policy="fail"
)
```

**Parameters:**
- `project_id` (required): Project ID or name
- `work_item_updates` (required): List of update operations (max 200)
- `validate_only` (optional): Only validate, don't update
- `bypass_rules` (optional): Skip validation rules (requires permissions)
- `suppress_notifications` (optional): Don't send email notifications
- `error_policy`: "fail" (stop on first error) or "omit" (skip failed items)

**JSON Patch Operations:**
- `"op": "replace"` - Replace field value
- `"op": "add"` - Add new field or array item
- `"op": "remove"` - Remove field or array item
- `"op": "test"` - Test field value (for conditional updates)

**Returns:** List of updated WorkItem objects

**Common Operations:**
```python
# Update title and description
{"op": "replace", "path": "/fields/System.Title", "value": "New Title"}
{"op": "replace", "path": "/fields/System.Description", "value": "Updated description"}

# Change state and assignment
{"op": "replace", "path": "/fields/System.State", "value": "Active"}
{"op": "replace", "path": "/fields/System.AssignedTo", "value": "user@company.com"}

# Set priority and tags
{"op": "replace", "path": "/fields/Microsoft.VSTS.Common.Priority", "value": 1}
{"op": "replace", "path": "/fields/System.Tags", "value": "urgent; bug; frontend"}

# Update custom fields
{"op": "replace", "path": "/fields/Custom.Component", "value": "Authentication"}
```

## Batch Deletion

### delete_work_items_batch

Delete or permanently destroy multiple work items.

```python
# Soft delete (move to recycle bin)
delete_work_items_batch(
    project_id="MyProject",
    work_item_ids=[123, 124, 125],
    destroy=False,
    error_policy="fail"
)

# Permanent deletion (destroy)
delete_work_items_batch(
    project_id="MyProject",
    work_item_ids=[123, 124, 125],
    destroy=True,
    error_policy="omit"
)
```

**Parameters:**
- `project_id` (required): Project ID or name
- `work_item_ids` (required): List of work item IDs to delete (max 200)
- `destroy` (optional): `false` = soft delete (recycle bin), `true` = permanent destruction
- `error_policy`: "fail" (stop on first error) or "omit" (skip failed items)

**Returns:** List of boolean values indicating success/failure for each work item (in order)

**⚠️ Warning:** `destroy=true` permanently deletes work items and **cannot be undone**!

## Query Syntax and WIQL

### WIQL (Work Item Query Language)

WIQL is SQL-like syntax for querying work items. Used in `query_work_items` tool.

**Basic Structure:**
```sql
SELECT [field1], [field2], ...
FROM WorkItems
WHERE [conditions]
ORDER BY [field]
```

**Common Field Names:**
- `[System.Id]` - Work item ID
- `[System.Title]` - Title
- `[System.WorkItemType]` - Type (Bug, Task, User Story, etc.)
- `[System.State]` - State (New, Active, Resolved, Closed)
- `[System.AssignedTo]` - Assigned user
- `[System.CreatedDate]` - Creation date
- `[System.ChangedDate]` - Last modified date
- `[System.AreaPath]` - Area path
- `[System.IterationPath]` - Iteration path
- `[Microsoft.VSTS.Common.Priority]` - Priority (1-4)
- `[System.Tags]` - Tags

**Example Queries:**

```sql
-- All active bugs assigned to current user
SELECT [System.Id], [System.Title], [System.State]
FROM WorkItems
WHERE [System.WorkItemType] = 'Bug'
  AND [System.State] = 'Active'
  AND [System.AssignedTo] = @Me

-- High priority items created in last 30 days
SELECT [System.Id], [System.Title], [Microsoft.VSTS.Common.Priority]
FROM WorkItems
WHERE [Microsoft.VSTS.Common.Priority] = 1
  AND [System.CreatedDate] >= @Today - 30

-- Items in specific area path
SELECT [System.Id], [System.Title], [System.AreaPath]
FROM WorkItems
WHERE [System.AreaPath] UNDER 'MyProject\\Web\\Frontend'

-- Items with specific tags
SELECT [System.Id], [System.Title], [System.Tags]
FROM WorkItems
WHERE [System.Tags] CONTAINS 'urgent'

-- Items by state and type
SELECT [System.Id], [System.Title], [System.State]
FROM WorkItems
WHERE [System.WorkItemType] IN ('Bug', 'Task')
  AND [System.State] NOT IN ('Closed', 'Removed')
ORDER BY [System.ChangedDate] DESC
```

**Special Variables:**
- `@Me` - Current authenticated user
- `@Today` - Current date
- `@CurrentIteration` - Current iteration

**Date Format:**
- Use simple date format: `'2024-01-15'` (not ISO format with time)
- Relative dates: `@Today - 7` (7 days ago)

### Simple Filtering (Alternative to WIQL)

For basic queries, use simple filtering with `query_work_items`:

```python
query_work_items(
    project_id="MyProject",
    simple_filter={
        "work_item_type": "Bug",
        "state": "Active",
        "assigned_to": "user@company.com",
        "area_path": "MyProject\\Web",
        "tags": "urgent; frontend",
        "created_after": "2024-01-01",
        "created_before": "2024-12-31"
    },
    page_size=50
)
```

## Performance and Limits

### API Limits

| Operation | Limit | Notes |
|-----------|-------|-------|
| Batch Size | 200 items | All batch operations |
| WIQL Results | 20,000 items | Default Azure DevOps limit |
| Query Timeout | 30 seconds | Server-side timeout |
| Field Count | No limit | But affects performance |

### Performance Guidelines

**Batch Operations:**
- **get_work_items_batch**: ~50-100 items/second
- **update_work_items_batch**: ~20-50 items/second  
- **delete_work_items_batch**: ~30-70 items/second

**Optimization Tips:**
1. **Use field filtering** in `get_work_items_batch` to reduce payload size
2. **Batch similar operations** together rather than individual calls
3. **Use "omit" error policy** for better performance with mixed valid/invalid IDs
4. **Monitor performance metrics** in logs for optimization opportunities

### Performance Monitoring

All batch operations log detailed performance metrics:

```json
{
  "operation_type": "batch_update",
  "total_duration": 2.45,
  "api_duration": 2.1,
  "requested_count": 50,
  "successful_count": 48,
  "success_rate": 96.0,
  "operations_per_second": 19.6,
  "avg_time_per_operation": 0.049
}
```

## Error Handling

### Error Policies

Both `"fail"` and `"omit"` policies are supported:

**"fail" (default for updates/deletes):**
- Stops on first error
- Returns exception with details
- Provides rollback information for manual cleanup
- Best for critical operations requiring all-or-nothing behavior

**"omit" (default for retrievals):**
- Skips failed items, continues with others
- Returns partial results
- Logs warnings for failed items
- Best for bulk operations where partial results are acceptable

### Common Error Scenarios

1. **Invalid work item IDs**: Items that don't exist or are not accessible
2. **Permission errors**: User lacks permission to read/modify items
3. **Validation failures**: Business rule violations (e.g., invalid state transitions)
4. **Field errors**: Invalid field names or values
5. **Concurrency conflicts**: Work item modified by another user

### Error Recovery

**For Updates with "fail" policy:**
- Check logs for successfully updated items
- Manually review/rollback if needed
- Retry failed operations after fixing issues

**For Operations with "omit" policy:**
- Review warning logs for failed items
- Separately handle failed items if needed
- Success/failure status in returned results

## Best Practices

### Batch Operations

1. **Start small**: Test with 5-10 items before scaling to 200
2. **Use appropriate error policies**: "fail" for critical updates, "omit" for bulk operations
3. **Monitor performance**: Watch logs for slow operations or low success rates
4. **Handle partial failures**: Always check returned results and logs

### WIQL Queries

1. **Use specific field lists**: Don't SELECT * - specify only needed fields
2. **Add appropriate WHERE clauses**: Avoid returning too many results
3. **Use proper date formats**: Simple YYYY-MM-DD format, not ISO
4. **Test queries incrementally**: Start simple, add complexity gradually

### Field Updates

1. **Use JSON Patch properly**: Understand operation types (replace vs add vs remove)
2. **Validate field names**: Use proper system and custom field reference names
3. **Handle state transitions**: Understand workflow rules before changing states
4. **Batch similar operations**: Group related updates together

### General Guidelines

1. **Check permissions**: Ensure user has appropriate access before bulk operations
2. **Use validation mode**: Test updates with `validate_only=true` first
3. **Plan for rollbacks**: Keep track of original values for critical updates
4. **Monitor API usage**: Be mindful of rate limits and server load
5. **Log operations**: Use structured logging for audit trails

### Error Prevention

1. **Validate inputs**: Check work item IDs and field values before API calls
2. **Use appropriate timeouts**: Allow sufficient time for large operations
3. **Handle network issues**: Implement retry logic for transient failures
4. **Check API limits**: Ensure batch sizes stay within limits
5. **Test thoroughly**: Validate operations in non-production environments first

## Examples and Use Cases

### Bulk State Transitions

```python
# Move multiple bugs from Active to Resolved
work_item_updates = []
for bug_id in bug_ids:
    work_item_updates.append({
        "work_item_id": bug_id,
        "operations": [
            {"op": "replace", "path": "/fields/System.State", "value": "Resolved"},
            {"op": "replace", "path": "/fields/Microsoft.VSTS.Common.ResolvedReason", "value": "Fixed"}
        ]
    })

result = update_work_items_batch(
    project_id=project_id,
    work_item_updates=work_item_updates,
    error_policy="omit"  # Continue even if some items can't be updated
)
```

### Bulk Assignment

```python
# Assign multiple tasks to a team member
work_item_updates = []
for task_id in task_ids:
    work_item_updates.append({
        "work_item_id": task_id,
        "operations": [
            {"op": "replace", "path": "/fields/System.AssignedTo", "value": "developer@company.com"}
        ]
    })

result = update_work_items_batch(
    project_id=project_id,
    work_item_updates=work_item_updates,
    suppress_notifications=True  # Avoid spam
)
```

### Cleanup Operations

```python
# Find and delete old test work items
query_result = query_work_items(
    project_id=project_id,
    wiql_query="""
        SELECT [System.Id]
        FROM WorkItems
        WHERE [System.Title] CONTAINS 'TEST'
          AND [System.CreatedDate] < @Today - 90
          AND [System.State] = 'Closed'
    """
)

work_item_ids = [item["id"] for item in query_result["workItems"]]

if work_item_ids:
    deletion_results = delete_work_items_batch(
        project_id=project_id,
        work_item_ids=work_item_ids,
        destroy=False,  # Move to recycle bin first
        error_policy="omit"
    )
```

This comprehensive documentation should help users understand and effectively use the batch operations and query syntax for Azure DevOps work items.