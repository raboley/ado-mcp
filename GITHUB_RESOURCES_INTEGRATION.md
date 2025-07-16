# GitHub Resources Integration

## Overview

The MCP client has been enhanced with comprehensive GitHub resources integration capabilities. This enables dynamic control of Azure DevOps pipelines that use GitHub repositories as resources, including branch/tag selection, template parameters, and runtime variables.

## Key Features Added

### 1. **Pipeline Parameters Support**
- **Variables**: Runtime variables passed to pipeline execution
- **Template Parameters**: Control template behavior and tool versions
- **Branch Selection**: Specify which branch/tag to run pipeline from
- **Stages to Skip**: Skip specific stages during execution
- **Resources**: Control repository resources and their branches/tags

### 2. **GitHub Integration**
- **Repository Control**: Dynamically select branches and tags from GitHub repositories
- **Service Connection**: Seamless integration with existing GitHub service connections
- **Template Usage**: Support for templates like `raboley/tooling/.ado/steps/install.taskfile.yml`

### 3. **Enhanced MCP Tools**
All pipeline execution tools now support the new parameters:
- `run_pipeline`: Direct execution with full parameter control
- `run_pipeline_and_get_outcome`: Execute and wait with comprehensive parameters
- `run_pipeline_by_name`: Name-based execution with all features
- `run_pipeline_and_get_outcome_by_name`: Complete name-based execution

## Implementation Details

### New Model: `PipelineRunRequest`
```python
class PipelineRunRequest(BaseModel):
    resources: dict[str, Any] | None = None
    templateParameters: dict[str, Any] | None = None
    variables: dict[str, Any] | None = None
    stagesToSkip: list[str] | None = None
    branch: str | None = None
```

### Core Components Updated
1. **Pipeline Execution Layer** (`ado/pipelines/builds.py`)
2. **Client Interface** (`ado/client.py`)
3. **Name-based Lookups** (`ado/lookups.py`)
4. **MCP Tool Definitions** (`ado/tools.py`)

## Usage Examples

### Basic GitHub Resources Control
```python
# Run pipeline with GitHub resources
result = await mcp_client.call_tool("run_pipeline", {
    "project_id": "your-project-id",
    "pipeline_id": pipeline_id,
    "resources": {
        "repositories": {
            "tooling": {
                "refName": "refs/heads/main"  # or "refs/tags/v1.0.0"
            }
        }
    },
    "template_parameters": {
        "toolingBranch": "main",
        "taskfileVersion": "latest",
        "installPath": "./bin"
    },
    "variables": {
        "environment": "production",
        "testVariable": "github-resources-demo"
    }
})
```

### Branch/Tag Selection
```python
# Run from specific branch
result = await mcp_client.call_tool("run_pipeline", {
    "project_id": "your-project-id",
    "pipeline_id": pipeline_id,
    "branch": "refs/heads/feature/new-feature",
    "variables": {"environment": "development"}
})

# Run from specific tag
result = await mcp_client.call_tool("run_pipeline", {
    "project_id": "your-project-id",
    "pipeline_id": pipeline_id,
    "resources": {
        "repositories": {
            "tooling": {
                "refName": "refs/tags/v1.0.0"
            }
        }
    }
})
```

### Name-based Execution
```python
# Run by name with all features
result = await mcp_client.call_tool("run_pipeline_by_name", {
    "project_name": "ado-mcp",
    "pipeline_name": "github-resources-pipeline",
    "template_parameters": {
        "toolingBranch": "main",
        "taskfileVersion": "v3.30.1",
        "installPath": "./bin"
    },
    "variables": {
        "environment": "staging"
    }
})
```

## raboley/tooling Integration

### Template: `.ado/steps/install.taskfile.yml`
This template supports:
- **Version Control**: Specify exact Taskfile versions
- **Branch Selection**: Use different branches for different environments
- **Installation Paths**: Configure where tools are installed

### Parameters Supported
- `toolingBranch`: Controls which branch of the tooling repo to use
- `taskfileVersion`: Controls which version of Taskfile to install
- `installPath`: Controls installation directory

### Example Pipeline YAML
```yaml
resources:
  repositories:
    - repository: tooling
      type: github
      name: raboley/tooling
      endpoint: raboley
      ref: refs/heads/${{ parameters.toolingBranch }}

stages:
  - stage: InstallTools
    jobs:
      - job: InstallTaskfile
        steps:
          - template: tooling/.ado/steps/install.taskfile.yml
            parameters:
              version: ${{ parameters.taskfileVersion }}
              installPath: ${{ parameters.installPath }}
```

## Service Connection
- **Connection Name**: `raboley`
- **Connection ID**: `4361a434-cbc7-4fbc-ac27-9ea5027c0eaa`
- **Type**: GitHub
- **Repository Access**: `raboley/tooling`

## Testing

### Comprehensive Test Suite
1. **Basic Functionality** (`test_pipeline_run_params.py`)
   - Variables support
   - Template parameters
   - Branch selection
   - Backward compatibility

2. **GitHub Resources** (`test_github_resources.py`)
   - Branch/tag selection
   - Template integration
   - Name-based execution

3. **Capability Validation** (`test_resources_capability.py`)
   - Resources parameter
   - Comprehensive parameter support
   - Error handling

4. **Integration Demo** (`test_github_resources_demo.py`)
   - Complete workflow demonstration
   - Multiple scenario testing

### Test Results
- ✅ All existing tests continue to pass
- ✅ New functionality fully tested
- ✅ Backward compatibility maintained
- ✅ GitHub resources integration confirmed

## Benefits

### For Users
- **Dynamic Control**: Change repository branches/tags at runtime
- **Version Management**: Control tool versions through parameters
- **Environment Flexibility**: Use different configurations for different environments
- **Simplified Execution**: Name-based pipeline execution with full parameter control

### For Developers
- **Comprehensive API**: All pipeline execution methods support full parameter set
- **Consistent Interface**: Same parameters across all execution methods
- **Extensible Design**: Easy to add new parameters in the future
- **Robust Testing**: Comprehensive test coverage for all scenarios

## Future Enhancements

### Potential Additions
1. **Tag Pattern Matching**: Support for semantic version patterns
2. **Resource Caching**: Cache repository resources for better performance
3. **Parameter Validation**: Enhanced validation for template parameters
4. **Batch Operations**: Execute multiple pipelines with different parameters

### Integration Opportunities
1. **CI/CD Workflows**: Automated pipeline execution with dynamic parameters
2. **Environment Promotion**: Use different branches for different environments
3. **Tool Management**: Centralized tool version control through templates
4. **Configuration Management**: Dynamic configuration through variables

## Conclusion

The GitHub resources integration provides a powerful and flexible way to control Azure DevOps pipelines that use GitHub repositories as resources. The implementation maintains backward compatibility while adding comprehensive new capabilities, making it easy to adopt in existing workflows.

The MCP client can now:
- ✅ Control GitHub repository branches and tags dynamically
- ✅ Pass template parameters for tool version control
- ✅ Set runtime variables for environment configuration
- ✅ Execute pipelines with comprehensive parameter control
- ✅ Support both ID-based and name-based pipeline execution

This enables sophisticated CI/CD workflows with the `raboley/tooling` repository and `.ado/steps/install.taskfile.yml` template, providing dynamic control over tool versions, installation paths, and execution environments.