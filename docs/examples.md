# Examples

This page provides practical examples of using ADO MCP in different scenarios.

## Basic Examples

### List All Projects

```python
# Through your AI assistant:
"Show me all projects in my Azure DevOps organization"

# This uses the list_projects tool internally
```

### Run a Specific Pipeline

```python
# Through your AI assistant:
"Run the 'deploy-staging' pipeline in the 'MyWebApp' project"

# This uses find_project_by_name and find_pipeline_by_name, then run_pipeline
```

## Pipeline Analysis Examples

### Analyze a Failed Build

```python
# Through your AI assistant:
"Analyze this failed build: https://dev.azure.com/MyOrg/MyProject/_build/results?buildId=123"

# This extracts the build ID and uses:
# 1. get_build_by_id to get pipeline information
# 2. get_pipeline_failure_summary for analysis
# 3. get_failed_step_logs for detailed logs
```

### Compare Pipeline Runs

```python
# Through your AI assistant:
"Compare the last two runs of the 'ci-pipeline' in the 'Backend' project"

# This uses:
# 1. find_pipeline_by_name to locate the pipeline
# 2. Multiple get_pipeline_run calls
# 3. Analysis of differences between runs
```

## Advanced Examples

### Monitor Pipeline with Custom Timeout

```python
# Through your AI assistant:
"Run the 'long-integration-test' pipeline and wait up to 30 minutes for completion"

# This uses run_pipeline_and_get_outcome with custom timeout
```

### Generate Weekly Report

```python
# Through your AI assistant:
"Generate a report of all pipeline failures in the 'Production' project from last week"

# This uses:
# 1. list_pipelines to get all pipelines
# 2. Multiple pipeline run queries
# 3. Failure analysis aggregation
```

## Working with Logs

### Get Specific Step Logs

```python
# Through your AI assistant:
"Show me the logs for the 'Run Tests' step in build 456"

# This uses:
# 1. get_pipeline_timeline to find the step
# 2. get_failed_step_logs with step name filter
```

### Search Logs for Patterns

```python
# Through your AI assistant:
"Find all error messages containing 'connection timeout' in the last build"

# This uses:
# 1. list_pipeline_logs to get all logs
# 2. get_log_content_by_id for each log
# 3. Pattern matching across log content
```

## Troubleshooting Examples

### Debug Authentication Issues

```python
# Through your AI assistant:
"Why am I getting authentication errors when trying to run pipelines?"

# This uses:
# 1. check_authentication to verify credentials
# 2. Analysis of error patterns
# 3. Suggestions for resolution
```

### Identify Resource Bottlenecks

```python
# Through your AI assistant:
"Which pipelines are taking the longest to run in the 'Development' project?"

# This uses:
# 1. list_pipelines for the project
# 2. get_pipeline_run for recent runs
# 3. Timeline analysis for duration patterns
```

## Integration Examples

### CI/CD Health Dashboard

```python
# Through your AI assistant:
"Create a health summary of all deployment pipelines across all projects"

# This uses:
# 1. list_projects to get all projects
# 2. list_pipelines for each project
# 3. Recent run analysis for health metrics
```

### Failure Trend Analysis

```python
# Through your AI assistant:
"Show me the trend of test failures over the last month for the 'API' project"

# This uses:
# 1. Historical pipeline run data
# 2. Failure pattern analysis
# 3. Trend visualization suggestions
```

## URL-Based Examples

### Extract Pipeline from Build URL

```python
# Through your AI assistant:
"What pipeline generated this build? https://dev.azure.com/MyOrg/MyProject/_build/results?buildId=789"

# This uses:
# 1. URL parsing to extract components
# 2. get_build_by_id to get pipeline information
# 3. get_pipeline for detailed pipeline data
```

### Batch Analysis from Multiple URLs

```python
# Through your AI assistant:
"Analyze these three failed builds:
- https://dev.azure.com/MyOrg/Proj1/_build/results?buildId=100
- https://dev.azure.com/MyOrg/Proj1/_build/results?buildId=101
- https://dev.azure.com/MyOrg/Proj2/_build/results?buildId=50"

# This processes each URL and provides comparative analysis
```

## Performance Examples

### Cached vs Fresh Data

```python
# The MCP server automatically caches project and pipeline lists
# Fresh data is fetched when cache expires or when explicitly requested

# Through your AI assistant:
"Get the latest pipeline list for 'MyProject' (force refresh)"
# vs
"Show me the pipelines in 'MyProject'"  # Uses cache if available
```

### Batch Operations

```python
# Through your AI assistant:
"Get the status of all pipelines that ran today across all projects"

# This efficiently batches:
# 1. Project enumeration
# 2. Pipeline discovery
# 3. Recent run queries
# 4. Status aggregation
```