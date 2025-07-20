# Test Cleanup Checklist

This document tracks the cleanup of all test files to ensure they follow the testing methodology in CLAUDE.md.

## Test Quality Standards to Apply:
- [ ] Remove docstrings from test functions
- [ ] Remove comments explaining test steps
- [ ] Remove print statements or celebratory output
- [ ] Ensure proper assertion messages with context
- [ ] Test actual end results, not just that something didn't crash
- [ ] Make failure messages informative for debugging

## Test Files Cleaned Up - ALL COMPLETED! ✅

### Core Tests (7/7) ✅
- [x] tests/test_caching.py
- [x] tests/test_caching_e2e.py
- [x] tests/test_helpers.py
- [x] tests/test_production_features.py
- [x] tests/test_resources_capability.py
- [x] tests/test_server.py
- [x] tests/test_pipeline_run_params.py

### ADO Client Tests (1/1) ✅
- [x] tests/ado/test_client.py

### Organization Tests (2/2) ✅
- [x] tests/organization/test_set_organization.py
- [x] tests/organization/test_check_authentication.py

### Project Tests (1/1) ✅
- [x] tests/projects/test_list_projects.py

### Pipeline Tests (2/2) ✅
- [x] tests/pipelines/test_list_pipelines.py
- [x] tests/pipelines/test_get_pipeline.py

### Pipeline Run Tests (4/4) ✅
- [x] tests/pipeline_runs/test_run_pipeline.py
- [x] tests/pipeline_runs/test_get_pipeline_run.py
- [x] tests/pipeline_runs/test_run_pipeline_by_name.py
- [x] tests/pipeline_runs/test_run_pipeline_with_parameters.py

### Preview Tests (3/3) ✅
- [x] tests/preview/test_preview_pipeline_yaml_override.py
- [x] tests/preview/test_preview_pipeline_github_resources.py
- [x] tests/preview/test_preview_pipeline_basic.py

### Build Tests (1/1) ✅
- [x] tests/builds/test_get_build_by_id.py

### Log Tests (1/1) ✅
- [x] tests/logs/test_get_pipeline_failure_summary.py

### Service Connection Tests (1/1) ✅
- [x] tests/service_connections/test_list_service_connections.py

## TOTAL: 23/23 TEST FILES COMPLETED ✅

## Workflow:
1. For each test file, make the necessary changes
2. Run the individual test to ensure it still passes: `task test-single TEST_NAME=path::to::test`
3. Check off the item when complete
4. After all files are cleaned, run full test suite with `task test`