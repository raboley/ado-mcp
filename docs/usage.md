# Usage Guide

Once ADO MCP is installed and configured, you can use it through your AI assistant to interact with Azure DevOps. Here are common usage patterns and examples.

## Basic Operations

### List Projects

Ask your AI assistant to show all projects in your organization:

```
Show me all Azure DevOps projects in my organization.
```

### Find and Run Pipelines

```
Find the "deploy-production" pipeline in the "MyApp" project and run it.
```

### Check Build Status

```
What pipelines have failed recently? Show me the failure details.
```

## Pipeline Analysis

### Analyze Failed Builds

You can analyze builds directly from Azure DevOps URLs:

```
Analyze this failed build: https://dev.azure.com/MyOrg/MyProject/_build/results?buildId=123
```

### Get Detailed Logs

```
Show me the detailed logs for the failed steps in pipeline run 456.
```

### Root Cause Analysis

```
Help me understand why the "build-and-test" pipeline keeps failing on the test step.
```

## Advanced Operations

### Monitor Pipeline Execution

```
Run the "integration-tests" pipeline and monitor its progress. Alert me when it completes.
```

### Generate Reports

```
Generate a summary of all deployment pipeline runs from the last week.
```

### Compare Runs

```
Compare the latest run of "ci-pipeline" with the previous successful run.
```

## Working with Azure DevOps URLs

### Understanding URL Structure

Azure DevOps URLs contain important information:

**Example**: `https://dev.azure.com/RussellBoley/ado-mcp/_build/results?buildId=324`

- **Organization**: `RussellBoley`
- **Project**: `ado-mcp`
- **Build/Run ID**: `324` (from `buildId` parameter)

### Getting Pipeline Information from URLs

The MCP server can extract pipeline information from build URLs:

1. **Extract URL components** automatically
2. **Use build ID to find pipeline** definition
3. **Access pipeline-specific operations**

```
What pipeline does this build belong to? https://dev.azure.com/MyOrg/MyProject/_build/results?buildId=324
```

## Available Tools

### Project Operations
- `list_projects` - Get all projects in the organization
- `find_project_by_name` - Find project using fuzzy matching

### Pipeline Operations
- `list_pipelines` - Get all pipelines in a project
- `find_pipeline_by_name` - Find pipeline using fuzzy matching
- `get_pipeline` - Get detailed pipeline information
- `run_pipeline` - Execute a pipeline
- `preview_pipeline` - Preview pipeline without running

### Build Operations
- `get_pipeline_run` - Get details of a specific run
- `get_build_by_id` - Get build information from build ID
- `run_pipeline_and_get_outcome` - Run and wait for completion

### Log and Analysis Operations
- `get_pipeline_failure_summary` - Intelligent failure analysis
- `get_failed_step_logs` - Get logs for failed steps
- `get_pipeline_timeline` - Get execution timeline
- `list_pipeline_logs` - List all available logs
- `get_log_content_by_id` - Get specific log content

### Service Connections
- `list_service_connections` - Get service connections for a project

## Best Practices

### Authentication
- Use Azure CLI authentication (`az devops login`) for better security
- Ensure your PAT has appropriate scopes if using token authentication
- Regularly rotate your Personal Access Tokens

### Performance
- The server uses intelligent caching to speed up repeated operations
- Name-based lookups use fuzzy matching for flexibility
- Batch operations are optimized for efficiency

### Error Handling
- The server provides detailed error messages and suggestions
- Failed operations include context for troubleshooting
- Authentication errors provide clear next steps