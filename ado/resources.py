"""
MCP Resources for providing documentation and guidance to LLM clients.

This module defines resources that will be available to LLMs using this MCP server,
providing comprehensive guidance on how to work with Azure DevOps operations.
"""

import logging

logger = logging.getLogger(__name__)


def register_mcp_resources(mcp_instance):
    """Register MCP resources that provide documentation and guidance to LLMs."""

    @mcp_instance.resource("ado://user-guide/getting-started")
    def getting_started_guide():
        """Essential getting started guide for Azure DevOps MCP operations."""
        return """# Azure DevOps MCP - Getting Started Guide

## 🎯 Quick Start for LLMs

When a user provides Azure DevOps information, follow this decision tree:

### 1. User Provides a URL
✅ **USE: `analyze_pipeline_input`**
- Pass the full URL as `user_input`
- This will automatically parse and guide you to the right next steps

### 2. User Mentions Pipeline Name
✅ **USE: `find_pipeline_by_name`**
- Search for pipelines by name with fuzzy matching
- Get pipeline_id for further operations

### 3. User Provides Build Number Only
✅ **USE: `analyze_pipeline_input`**
- Pass the build number as `user_input`
- Will guide you to use `get_build_by_id`

### 4. User Wants to Analyze a Specific Run
✅ **USE: `resolve_pipeline_from_url`** (if URL provided)
- OR use `get_build_by_id` + `get_pipeline_failure_summary`

## 🚫 Common Mistakes to Avoid

❌ **DON'T** try to guess pipeline_id from build_id
❌ **DON'T** use `get_pipeline_run` without first getting the correct pipeline_id
❌ **DON'T** assume buildId in URL = pipeline_id (it's actually run_id!)

## ✅ Always Start With These Helper Tools

1. **`analyze_pipeline_input`** - For any user input
2. **`resolve_pipeline_from_url`** - For URLs specifically
3. **`find_pipeline_by_name`** - For pipeline name searches

These tools will guide you to the specific low-level tools needed.
"""

    @mcp_instance.resource("ado://user-guide/url-patterns")
    def url_patterns_guide():
        """Guide for handling different Azure DevOps URL patterns."""
        return """# Azure DevOps URL Patterns Guide

## Common URL Types You'll Encounter

### Build Results URL (Most Common)
```
https://dev.azure.com/Org/Project/_build/results?buildId=324&view=results
```
- **Organization**: Org
- **Project**: Project
- **buildId=324**: This is a RUN ID (specific execution)
- **Next Step**: Use `resolve_pipeline_from_url` or `analyze_pipeline_input`

### Pipeline Definition URL
```
https://dev.azure.com/Org/Project/_build/definition?definitionId=84&_a=summary
```
- **definitionId=84**: This is the PIPELINE ID
- **Next Step**: Use `get_pipeline` with this pipeline_id

### Build Hub URL
```
https://dev.azure.com/Org/Project/_build
```
- **Next Step**: Use `list_pipelines` to see available pipelines

## Workflow for URL Processing

1. **Parse with `analyze_pipeline_input`**:
   ```
   analyze_pipeline_input(user_input="<full_url>")
   ```

2. **Or use `resolve_pipeline_from_url`** for complete resolution:
   ```
   resolve_pipeline_from_url(url="<full_url>")
   ```

3. **Follow the suggested_actions** in the response

## ID Mapping Reference

- **buildId** (in URL) = **run_id** (in tools)
- **definitionId** (in URL) = **pipeline_id** (in tools)
- **project name** (in URL) → need to map to **project_id** (UUID)
"""

    @mcp_instance.resource("ado://workflows/failure-analysis")
    def failure_analysis_workflow():
        """Complete workflow for analyzing pipeline failures."""
        return """# Pipeline Failure Analysis Workflow

## When User Says: "Analyze this failed build"

### Step 1: Identify the Build
**If URL provided:**
```
resolve_pipeline_from_url(url="<user_provided_url>")
```

**If build number provided:**
```
analyze_pipeline_input(user_input="<build_number>")
```

### Step 2: Get Failure Summary
```
get_pipeline_failure_summary(
    project_id="<from_step_1>",
    pipeline_id="<from_step_1>",
    run_id="<build_id_from_url>"
)
```

### Step 3: Get Detailed Logs (if needed)
```
get_failed_step_logs(
    project_id="<project_id>",
    pipeline_id="<pipeline_id>",
    run_id="<run_id>",
    step_name="<specific_step>"  # optional filter
)
```

### Step 4: Present Analysis
- Root cause tasks from failure summary
- Specific error messages from logs
- Suggested fixes based on error patterns

## Key Fields in Failure Summary

- **root_cause_tasks**: The actual failing steps
- **hierarchy_failures**: Parent jobs/stages that failed due to children
- **total_failed_steps**: Overall failure count
- **issues**: Categorized error information
"""

    @mcp_instance.resource("ado://workflows/pipeline-execution")
    def pipeline_execution_workflow():
        """Complete workflow for running and monitoring pipelines."""
        return """# Pipeline Execution Workflow

## When User Says: "Run this pipeline"

### Step 1: Identify the Pipeline
**If URL provided:**
```
resolve_pipeline_from_url(url="<user_provided_url>")
```

**If pipeline name provided:**
```
find_pipeline_by_name(
    pipeline_name="<user_provided_name>",
    project_id="<project_id>"
)
```

### Step 2: Choose Execution Method

**Fire and Forget:**
```
run_pipeline(
    project_id="<project_id>",
    pipeline_id="<pipeline_id>"
)
```

**Run and Wait for Completion:**
```
run_pipeline_and_get_outcome(
    project_id="<project_id>",
    pipeline_id="<pipeline_id>",
    timeout_seconds=300
)
```

### Step 3: Monitor Progress (if using fire-and-forget)
```
get_pipeline_run(
    project_id="<project_id>",
    pipeline_id="<pipeline_id>",
    run_id="<run_id_from_step_2>"
)
```

## Execution Options

- **`run_pipeline`**: Quick start, returns immediately
- **`run_pipeline_and_get_outcome`**: Full execution with analysis
- **`preview_pipeline`**: See what would run without executing
"""

    @mcp_instance.resource("ado://reference/tool-mapping")
    def tool_mapping_reference():
        """Reference for mapping user requests to specific tools."""
        return """# Tool Mapping Reference

## Smart Helper Tools (Start Here)

| User Input | Recommended Tool | Purpose |
|------------|------------------|---------|
| Any URL | `analyze_pipeline_input` | Parse and guide next steps |
| Pipeline name | `find_pipeline_by_name` | Find pipeline by name |
| Build number | `analyze_pipeline_input` | Identify build and pipeline |
| Mixed text | `analyze_pipeline_input` | Extract all relevant info |

## Specific Operation Tools

### Pipeline Information
- **`get_pipeline`**: Get pipeline definition details
- **`list_pipelines`**: See all pipelines in project
- **`get_build_by_id`**: Map build/run ID to pipeline ID

### Pipeline Execution
- **`run_pipeline`**: Start pipeline execution
- **`run_pipeline_and_get_outcome`**: Run and wait for completion
- **`preview_pipeline`**: Preview without executing

### Run Analysis
- **`get_pipeline_run`**: Get run details
- **`get_pipeline_failure_summary`**: Analyze failures
- **`get_failed_step_logs`**: Get specific error logs
- **`get_pipeline_timeline`**: See execution timeline

### Logs and Debugging
- **`list_pipeline_logs`**: List all available logs
- **`get_log_content_by_id`**: Get specific log content

## Project Management
- **`list_projects`**: See available projects
- **`set_ado_organization`**: Switch organizations

## Decision Matrix

| User Says... | Use This Tool |
|--------------|---------------|
| "Analyze this URL" | `resolve_pipeline_from_url` |
| "Why did X fail?" | `get_pipeline_failure_summary` |
| "Run pipeline Y" | `find_pipeline_by_name` → `run_pipeline` |
| "Show me the logs" | `get_failed_step_logs` |
| "What pipelines exist?" | `list_pipelines` |
"""

    @mcp_instance.resource("ado://examples/common-scenarios")
    def common_scenarios_examples():
        """Real examples of common Azure DevOps scenarios."""
        return """# Common Scenarios with Examples

## Scenario 1: User Provides Build Results URL

**User**: "Can you analyze this failed build? https://dev.azure.com/MyOrg/MyProject/_build/results?buildId=1234"

**LLM Response**:
```
1. analyze_pipeline_input(user_input="https://dev.azure.com/MyOrg/MyProject/_build/results?buildId=1234")
2. Follow suggested_actions from response
3. Use get_pipeline_failure_summary with extracted IDs
4. Present root cause analysis
```

## Scenario 2: User Mentions Pipeline Name

**User**: "Run the 'CI Build Pipeline' for me"

**LLM Response**:
```
1. find_pipeline_by_name(pipeline_name="CI Build Pipeline", project_id="<project_id>")
2. Use returned pipeline_id with run_pipeline
3. Monitor execution with get_pipeline_run
```

## Scenario 3: User Provides Build Number Only

**User**: "What happened with build 1234?"

**LLM Response**:
```
1. analyze_pipeline_input(user_input="1234")
2. Follow guidance to use get_build_by_id
3. Extract pipeline_id and use get_pipeline_failure_summary
```

## Scenario 4: User Wants to See Logs

**User**: "Show me the logs for the failed test step"

**LLM Response**:
```
1. First identify the build/run (previous scenarios)
2. get_failed_step_logs(step_name="test") for filtered logs
3. get_log_content_by_id for specific log details
```

## Error Handling Examples

**If project not found**:
```
Use list_projects() to show available projects
Ask user to specify correct project
```

**If pipeline name is ambiguous**:
```
find_pipeline_by_name returns multiple matches
Present options to user with confidence scores
```

**If URL is invalid**:
```
analyze_pipeline_input will return error details
Guide user to provide correct URL format
```
"""
