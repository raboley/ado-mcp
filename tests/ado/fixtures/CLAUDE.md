# Test Pipeline Guidelines for Azure DevOps

This document provides guidelines for creating and managing test pipelines in Azure DevOps for the ado-mcp project.

## Essential Requirements

### 1. Pipeline URL Reference
**Every pipeline MUST have a URL comment at the top** that points to the pipeline in Azure DevOps.

Example:
```yaml
# Pipeline URL: https://dev.azure.com/RussellBoley/ado-mcp/_build?definitionId=59
name: test_run_and_get_pipeline_run_details
```

### 2. Use Server Jobs Only
**All test pipelines MUST run using Server jobs** - no agent-based jobs unless absolutely necessary.

Server jobs are faster and don't require waiting for agent allocation. See the fast test pipeline for an example:

```yaml
jobs:
- job: DelayJob
  pool: server  # This is a server job
  steps:
  - task: Delay@1
    inputs:
      delayForMinutes: '0'  # Always use 0 minutes for fast execution
```

### 3. Fast Execution with Delay Task
**Always use the Delay task with 0 minutes** to ensure test pipelines execute as quickly as possible.

```yaml
- task: Delay@1
  inputs:
    delayForMinutes: '0'  # MUST be 0 for fast tests
```

### 4. Sequential Execution Constraint
**Important:** Only one test pipeline can run at a time in our test suite. Therefore:
- Minimize execution time for all pipelines
- Use server jobs whenever possible
- Keep delay tasks at 0 minutes

### 5. Naming Convention for Slow Pipelines
Pipelines that MUST use Azure DevOps agents (not server jobs) should be **prefixed with `slow.`**

These are pipelines that:
- Need to grab actual logs from executed scripts
- Execute scripts or commands on Azure DevOps agents
- Perform actual build/test operations

Example naming:
- `slow.test_log_retrieval`
- `slow.test_script_execution`
- `slow.test_build_with_logs`

## Example Fast Test Pipeline

```yaml
# Pipeline URL: https://dev.azure.com/RussellBoley/ado-mcp/_build?definitionId=59
name: test_run_and_get_pipeline_run_details

trigger: none

variables:
  testVariable: 'default value'

jobs:
- job: DelayJob
  pool: server
  steps:
  - task: Delay@1
    inputs:
      delayForMinutes: '0'
```

## Example Slow Test Pipeline (Agent-based)

```yaml
# Pipeline URL: https://dev.azure.com/RussellBoley/ado-mcp/_build?definitionId=123
name: slow.test_script_execution

trigger: none

pool:
  vmImage: 'ubuntu-latest'  # Uses an agent, not server job

steps:
- script: |
    echo "This pipeline executes actual scripts"
    echo "It needs agent execution to capture logs"
  displayName: 'Run test script'
```

## Test Pipeline Categories

### Fast Pipelines (Server Jobs)
- Basic pipeline execution tests
- Parameter passing tests
- Resource configuration tests
- Template parameter tests
- Runtime variable tests

### Slow Pipelines (Agent Jobs)
- Log retrieval tests
- Script execution tests
- Build failure analysis tests
- Complex multi-stage tests with actual work

## Runtime Variables vs Template Parameters

When testing pipelines with dynamic values, understand the difference:

### Runtime Variables
- Set at **queue time** when running the pipeline
- Must be configured in Azure DevOps UI as "settable at queue time"
- Variables defined in YAML **cannot** be overridden at queue time
- Use `variables` parameter in `run_pipeline*` tools
- Example: `{"variables": {"testVar": "value"}}`

### Template Parameters  
- Defined in YAML with `parameters:` block
- Set when calling the pipeline
- More flexible for conditional logic in pipeline
- Use `template_parameters` parameter in `run_pipeline*` tools
- Example: `{"template_parameters": {"environment": "prod"}}`

### When to Use Each
- **Runtime Variables**: For simple value overrides (environment names, versions)
- **Template Parameters**: For pipeline logic control (enabling/disabling steps, conditional execution)

## Best Practices

1. **Always start with a server job** - only use agent jobs if absolutely necessary
2. **Document why** if a pipeline needs to be slow (agent-based)
3. **Keep pipelines minimal** - test only what's needed
4. **Use descriptive names** that indicate what the pipeline tests
5. **Include the pipeline URL** as the first line comment
6. **Test locally first** before creating in Azure DevOps

## Repository Resources in Pipeline Preview

When using the `preview_pipeline` MCP tool with repository resources:

### Repository Types and Authentication

**Public Repositories**: No authentication needed, `RepositoryType` is optional
**Private Repositories**: Authentication required, `RepositoryType` must be specified

### Supported Private Repository Types
- **"gitHub"**: GitHub repositories (automatic GITHUB_TOKEN injection if available)

### Resource Format

**Public repositories** (no authentication needed):
```python
resources = {
    "repositories": {
        "repo_name": {
            "refName": "refs/heads/branch_name"
            # No RepositoryType needed for public repos
        }
    }
}
```

**Private repositories** (authentication required):
```python
resources = {
    "repositories": {
        "repo_name": {
            "refName": "refs/heads/branch_name",
            "RepositoryType": "gitHub"  # Required for private repos
        }
    }
}
```

### Authentication Methods
- **GitHub Private Repos**: Automatically injects `GITHUB_TOKEN` from environment if available and no explicit token provided
- **Other Types**: Currently unsupported (Azure Repos, Bitbucket, etc.)

### Examples
```python
# Public GitHub repository (most common case)
resources = {
    "repositories": {
        "tooling": {
            "refName": "refs/heads/stable/0.0.1"
        }
    }
}

# Private GitHub repository with auto token injection
resources = {
    "repositories": {
        "tooling": {
            "refName": "refs/heads/main",
            "RepositoryType": "gitHub"
        }
    }
}

# Private GitHub repository with explicit token
resources = {
    "repositories": {
        "tooling": {
            "refName": "refs/heads/main",
            "RepositoryType": "gitHub",
            "token": "ghp_your_token_here",
            "tokenType": "Basic"
        }
    }
}
```

## Creating a New Test Pipeline

1. Start with the fst test pipeline template
2. Add your pipeline URL comment at the top
3. Modify only what's needed for your specific test
4. If you need agent execution, prefix the name with `slow.`
5. Always use 0-minute delays unless testing delay functionality itself
6. For azure devops to see the yaml commit and push any updates made.

Remember: The goal is to keep our test suite fast while maintaining comprehensive coverage!