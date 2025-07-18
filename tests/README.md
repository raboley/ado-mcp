# Azure DevOps MCP Test Suite

This directory contains the test suite for the Azure DevOps MCP (Model Context Protocol) implementation. Tests are organized by feature/tool category for better maintainability and clarity.

## Test Organization

### Directory Structure

```
tests/
├── organization/          # Organization & Authentication
├── projects/              # Project Management  
├── pipelines/             # Pipeline Management
├── pipeline_runs/         # Pipeline Execution
├── preview/               # Pipeline Preview
├── builds/                # Build Information
├── logs/                  # Logs & Failure Analysis
├── service_connections/   # Service Connections
├── helpers/               # Helper Tools (analyze_pipeline_input, etc.)
├── integration/           # Integration & Complex Scenarios
├── infrastructure/        # Infrastructure & Support
└── ado/                   # ADO Client Tests
```

### Test Categories

#### Organization & Authentication (`organization/`)
- `test_set_organization.py` - Tests for switching Azure DevOps organizations
- `test_check_authentication.py` - Tests for authentication verification

#### Project Management (`projects/`)
- `test_list_projects.py` - Tests for listing all projects
- Additional project-related tests to be added

#### Pipeline Management (`pipelines/`)
- `test_list_pipelines.py` - Tests for listing pipelines in a project
- `test_get_pipeline.py` - Tests for retrieving pipeline details

#### Pipeline Execution (`pipeline_runs/`)
- `test_run_pipeline.py` - Basic pipeline execution tests
- `test_run_pipeline_with_parameters.py` - Comprehensive parameter combination tests (consolidated from multiple GitHub resources tests)
- `test_run_pipeline_by_name.py` - Tests for name-based pipeline execution
- `test_get_pipeline_run.py` - Tests for retrieving run details

#### Pipeline Preview (`preview/`)
- `test_preview_pipeline_basic.py` - Basic preview functionality
- `test_preview_pipeline_yaml_override.py` - YAML override preview tests

#### Build Information (`builds/`)
- `test_get_build_by_id.py` - Tests for mapping build IDs to pipeline information

#### Logs & Failure Analysis (`logs/`)
- `test_get_pipeline_failure_summary.py` - Comprehensive failure analysis tests

#### Service Connections (`service_connections/`)
- `test_list_service_connections.py` - Tests for listing service connections

#### Helper Tools (`helpers/`)
- `test_analyze_pipeline_input.py` - Tests for URL and input analysis
- `test_find_pipeline_by_id_and_name.py` - Tests for fuzzy pipeline name matching

## Test Fixtures

### Known Working Pipelines
- **Pipeline 59** (`test_run_and_get_pipeline_run_details`): Basic pipeline, supports variables only
- **Pipeline 75** (`preview-test-parameterized`): Parameterized pipeline, may support variables and template parameters
- **Pipeline 200** (`github-resources-test-stable`): GitHub resources pipeline, supports template parameters but NOT variables

### Project IDs
- **ado-mcp project**: `49e895da-15c6-4211-97df-65c547a59c22`

## Running Tests

```bash
# Run all tests
task test

# Run tests for a specific category
uv run pytest tests/pipelines/ -v

# Run a specific test file
uv run pytest tests/pipeline_runs/test_run_pipeline.py -v

# Run tests matching a pattern
uv run pytest -k "github_resources" -v
```

## Test Patterns

### Authentication
All tests requiring Azure DevOps credentials use the `@requires_ado_creds` decorator. This ensures they're skipped when credentials aren't available.

### No-Auth Tests
Tests that verify behavior without authentication use the `mcp_client_no_auth` fixture, which properly unsets environment variables.

### Tool Registration Tests
Tool registration tests handle both potential response formats from the MCP client:
```python
tools_response = await client.list_tools()
if hasattr(tools_response, "tools"):
    tools = tools_response.tools
else:
    tools = tools_response
```

## Known Issues

Some tests are marked with `@pytest.mark.skip` due to pipeline-specific limitations:
- Feature branches that may not exist in external repositories
- Pipelines that don't support runtime variables
- Stages that don't exist in certain pipelines

These are not code issues but rather reflect the actual constraints of the test pipelines.