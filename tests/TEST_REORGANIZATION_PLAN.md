# Test Reorganization Plan

## Current State Analysis

### Test Files Overview
We currently have 20 test files with overlapping and unclear organization:

1. **Root directory tests** (should be moved):
   - `test_dynamic_resources.py`
   - `test_pipeline_basic.py`
   - `test_simple_github_pipeline.py`
   - `test_working_pipeline.py`

2. **Tests directory** (needs reorganization):
   - `test_azure_devops_api_comprehensive.py` - 447 lines, mixed tests
   - `test_azure_devops_preview_api_comprehensive.py` - 742 lines, preview tests
   - `test_github_resources*.py` (4 files) - redundant GitHub resources tests
   - `test_pipeline_resources_comprehensive.py` - resources parameter tests
   - `test_server.py` - 1800+ lines, tests ALL MCP tools
   - Various other mixed-purpose files

## Proposed Organization

### Directory Structure
```
tests/
├── organization/           # Organization & Authentication
│   ├── test_set_organization.py
│   └── test_check_authentication.py
├── projects/              # Project Management
│   ├── test_list_projects.py
│   ├── test_find_project_by_name.py
│   └── test_list_available_projects.py
├── pipelines/             # Pipeline Management
│   ├── test_list_pipelines.py
│   ├── test_get_pipeline.py
│   ├── test_create_pipeline.py
│   ├── test_delete_pipeline.py
│   ├── test_find_pipeline_by_name.py
│   └── test_list_available_pipelines.py
├── pipeline_runs/         # Pipeline Execution
│   ├── test_run_pipeline.py
│   ├── test_run_pipeline_with_parameters.py
│   ├── test_run_pipeline_by_name.py
│   ├── test_get_pipeline_run.py
│   └── test_run_pipeline_and_get_outcome.py
├── preview/               # Pipeline Preview
│   ├── test_preview_pipeline_basic.py
│   ├── test_preview_pipeline_yaml_override.py
│   └── test_preview_pipeline_with_parameters.py
├── builds/                # Build Information
│   ├── test_get_build_by_id.py
│   └── test_get_pipeline_timeline.py
├── logs/                  # Logs & Failure Analysis
│   ├── test_list_pipeline_logs.py
│   ├── test_get_log_content_by_id.py
│   ├── test_get_failed_step_logs.py
│   ├── test_get_pipeline_failure_summary.py
│   └── test_get_pipeline_failure_summary_by_name.py
├── service_connections/   # Service Connections
│   └── test_list_service_connections.py
├── helpers/               # Helper Tools
│   ├── test_analyze_pipeline_input.py
│   ├── test_find_pipeline_by_id_and_name.py
│   └── test_resolve_pipeline_from_url.py
├── integration/           # Integration & Complex Scenarios
│   ├── test_pipeline_lifecycle.py
│   ├── test_github_resources_integration.py
│   └── test_complex_scenarios.py
├── infrastructure/        # Infrastructure & Support
│   ├── test_authentication_providers.py
│   ├── test_caching.py
│   ├── test_retry_mechanism.py
│   └── test_error_handling.py
└── ado/                   # ADO Client Tests (existing)
    └── test_client.py
```

## Test Consolidation Plan

### 1. GitHub Resources Tests (REDUNDANT)
Currently have 4 files testing the same feature:
- `test_github_resources.py`
- `test_github_resources_demo.py`
- `test_github_resources_integration.py`
- `test_github_resources_simple.py`

**Action**: Consolidate into `pipeline_runs/test_run_pipeline_with_parameters.py`

### 2. Comprehensive Test Files (TOO LARGE)
- `test_server.py` (1800+ lines) - Split by tool
- `test_azure_devops_api_comprehensive.py` - Split by feature
- `test_azure_devops_preview_api_comprehensive.py` - Move to preview/

### 3. Failing Tests Analysis
Based on pytest results, failing tests are primarily:
- Pipeline 197, 200, 59, 75 with specific parameter combinations
- These appear to be pipeline-specific limitations, not code issues

**Action**: Create fixture pipelines with clear parameter support documentation

## Migration Strategy

### Phase 1: Create Structure
1. Create all directories ✓
2. Create placeholder __init__.py files
3. Document each tool's test requirements

### Phase 2: Split Large Files
1. Split test_server.py by MCP tool
2. Split comprehensive test files
3. Ensure no test logic is lost

### Phase 3: Consolidate Redundant Tests
1. Merge GitHub resources tests
2. Remove duplicate test cases
3. Keep best examples from each

### Phase 4: Fix Failing Tests
1. Identify pipeline parameter support
2. Update tests to use correct pipelines
3. Remove obsolete tests

### Phase 5: Documentation
1. Add README.md to each test directory
2. Document what each test covers
3. Document pipeline fixtures and their capabilities

## Expected Outcomes

1. **Clarity**: Each file tests one MCP tool
2. **No Redundancy**: Consolidated similar tests
3. **No Failures**: Only valid parameter combinations tested
4. **Easy Navigation**: Clear directory structure
5. **Better Coverage**: Easier to identify missing tests