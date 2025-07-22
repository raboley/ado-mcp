"""Query utility functions for Azure DevOps Work Items."""

from typing import Any, Dict, Optional


def build_wiql_from_filter(simple_filter: Dict[str, Any]) -> str:
    """
    Build a WIQL query from simple filter parameters.

    Args:
        simple_filter: Dictionary of filter criteria

    Returns:
        WIQL query string
    """
    # Base SELECT clause with common fields
    select_clause = (
        "SELECT [System.Id], [System.Title], [System.WorkItemType], "
        "[System.State], [System.AssignedTo], [System.CreatedDate], "
        "[System.AreaPath], [System.IterationPath], [System.Tags] "
        "FROM WorkItems"
    )

    conditions = []

    # Add conditions based on filter parameters
    if "work_item_type" in simple_filter:
        work_item_type = simple_filter["work_item_type"]
        conditions.append(f"[System.WorkItemType] = '{work_item_type}'")

    if "state" in simple_filter:
        state = simple_filter["state"]
        conditions.append(f"[System.State] = '{state}'")

    if "assigned_to" in simple_filter:
        assigned_to = simple_filter["assigned_to"]
        conditions.append(f"[System.AssignedTo] = '{assigned_to}'")

    if "area_path" in simple_filter:
        area_path = simple_filter["area_path"]
        conditions.append(f"[System.AreaPath] UNDER '{area_path}'")

    if "iteration_path" in simple_filter:
        iteration_path = simple_filter["iteration_path"]
        conditions.append(f"[System.IterationPath] UNDER '{iteration_path}'")

    if "tags" in simple_filter:
        tags = simple_filter["tags"]
        # Handle both single tag and semicolon-separated tags
        if ";" in tags:
            tag_conditions = []
            for tag in tags.split(";"):
                tag = tag.strip()
                if tag:
                    tag_conditions.append(f"[System.Tags] CONTAINS '{tag}'")
            if tag_conditions:
                conditions.append(f"({' OR '.join(tag_conditions)})")
        else:
            conditions.append(f"[System.Tags] CONTAINS '{tags.strip()}'")

    if "created_after" in simple_filter:
        created_after = simple_filter["created_after"]
        conditions.append(f"[System.CreatedDate] >= '{created_after}'")

    if "created_before" in simple_filter:
        created_before = simple_filter["created_before"]
        conditions.append(f"[System.CreatedDate] <= '{created_before}'")

    # Build final query
    if conditions:
        where_clause = " WHERE " + " AND ".join(conditions)
        query = select_clause + where_clause
    else:
        query = select_clause

    # Add ordering - use creation date for better recency sorting
    if "created_after" in simple_filter or "created_before" in simple_filter:
        # Date-filtered queries should show most recent first
        query += " ORDER BY [System.CreatedDate] DESC"
    elif "assigned_to" in simple_filter:
        # User-specific queries should show most recent first
        query += " ORDER BY [System.CreatedDate] DESC"
    else:
        # Default to ID ordering for general queries
        query += " ORDER BY [System.Id]"

    return query


def analyze_query_complexity(
    wiql_query: Optional[str],
    simple_filter: Optional[Dict[str, Any]],
    top: Optional[int],
    skip: Optional[int],
) -> Dict[str, Any]:
    """
    Analyze query complexity for performance metrics.

    Args:
        wiql_query: The WIQL query string
        simple_filter: Simple filter dictionary
        top: Maximum results to return
        skip: Number of results to skip

    Returns:
        Dictionary with complexity metrics
    """
    complexity = {
        "filter_condition_count": 0,
        "has_text_search": False,
        "has_date_filter": False,
        "has_complex_joins": False,
        "estimated_complexity": "low",
    }

    # Analyze simple filter complexity
    if simple_filter:
        complexity["filter_condition_count"] = len(simple_filter)

        # Check for date filters
        if any(key in simple_filter for key in ["created_after", "created_before"]):
            complexity["has_date_filter"] = True

        # Check for text searches (tags, assigned_to)
        if any(key in simple_filter for key in ["tags", "assigned_to"]):
            complexity["has_text_search"] = True

    # Analyze WIQL query complexity
    if wiql_query:
        query_upper = wiql_query.upper()

        # Count WHERE conditions
        where_count = (
            query_upper.count(" AND ")
            + query_upper.count(" OR ")
            + (1 if " WHERE " in query_upper else 0)
        )
        complexity["filter_condition_count"] = max(
            complexity["filter_condition_count"], where_count
        )

        # Check for complex operations
        complex_operations = ["JOIN", "UNION", "CONTAINS", "LIKE", "UNDER", "IN"]
        for op in complex_operations:
            if op in query_upper:
                complexity["has_complex_joins"] = True
                break

        # Check for date operations
        if any(
            date_op in query_upper
            for date_op in ["CREATEDDATE", "CHANGEDDATE", ">", "<", ">=", "<="]
        ):
            complexity["has_date_filter"] = True

        # Check for text search operations
        if any(text_op in query_upper for text_op in ["CONTAINS", "LIKE", "TAGS", "ASSIGNEDTO"]):
            complexity["has_text_search"] = True

    # Determine overall complexity
    complexity_score = 0
    if complexity["filter_condition_count"] > 3:
        complexity_score += 2
    elif complexity["filter_condition_count"] > 1:
        complexity_score += 1

    if complexity["has_text_search"]:
        complexity_score += 1
    if complexity["has_date_filter"]:
        complexity_score += 1
    if complexity["has_complex_joins"]:
        complexity_score += 2

    # Large pagination can be expensive
    if skip and skip > 1000:
        complexity_score += 1
    if top and top > 500:
        complexity_score += 1

    if complexity_score >= 4:
        complexity["estimated_complexity"] = "high"
    elif complexity_score >= 2:
        complexity["estimated_complexity"] = "medium"
    else:
        complexity["estimated_complexity"] = "low"

    return complexity