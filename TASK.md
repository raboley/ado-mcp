### Task List

*   [x] **Feature: Foundational Server & ADO Client Setup**
    *   **Functionality:** Initialize the main MCP server in `server.py` and the `AdoClient` in `ado/client.py`.
    *   **Functionality:** Implement a `check_authentication` method in `AdoClient` to verify the PAT is valid.
    *   **Testing:** In `tests/ado/test_client.py`, write tests for `AdoClient` initialization (with and without PAT) and for `check_authentication` (success and failure cases).
    *   **Documentation:** Add docstrings for the initial server, `AdoClient`, and `check_authentication` method.

*   [x] **Feature: List ADO Projects**
    *   **Functionality:** Implement a `list_projects` method in `ado/client.py` to call the [projects list](https://learn.microsoft.com/en-us/rest/api/azure/devops/core/projects/list?view=azure-devops-rest-7.2) API.
    *   **Tooling:** Create a `projects/list` tool in `ado/tools.py` that uses the `list_projects` client method.
    *   **Testing:** Write a unit test in `tests/ado/test_client.py` for `list_projects`. Write an integration test in `tests/test_server.py` for the `projects/list` tool.
    *   **Documentation:** Add docstrings for the `list_projects` method and the `projects/list` tool.

*   [x] **Feature: List ADO Pipelines**
    *   **Functionality:** Implement a `list_pipelines` method in `ado/client.py` to call the [pipelines list](https://learn.microsoft.com/en-us/rest/api/azure/devops/pipelines/pipelines/list?view=azure-devops-rest-7.2) API.
    *   **Tooling:** Create a `pipelines/list` tool in `ado/tools.py`.
    *   **Testing:** Write a unit test for `list_pipelines` and an integration test for the `pipelines/list` tool.
    *   **Documentation:** Add docstrings for the method and tool.

*   [x] **Feature: Get Pipeline Details**
    *   **Functionality:** Implement `get_pipeline` in `ado/client.py` using the [pipelines get](https://learn.microsoft.com/en-us/rest/api/azure/devops/pipelines/pipelines/get?view=azure-devops-rest-7.2) API.
    *   **Tooling:** Create a `pipelines/get` tool in `ado/tools.py`.
    *   **Testing:** Write a unit test for `get_pipeline` and an integration test for the `pipelines/get` tool.
    *   **Documentation:** Add docstrings for the method and tool.

*   [x] **Feature: Create a Pipeline**
    * [x] Create a simple azure pipeline yaml that finishes as quickly as possible using azure devops server jobs that do nothing
    * [x] **Functionality:** Implement `create_pipeline` in `ado/client.py` 

*   [x] **Feature: Run a Pipeline**
    *   **Functionality:** Implement `run_pipeline` in `ado/client.py` using the [run pipeline](https://learn.microsoft.com/en-us/rest/api/azure/devops/pipelines/runs/run-pipeline?view=azure-devops-rest-7.2) API.
    *   **Tooling:** Create a `pipelines/run` tool in `ado/tools.py`.
    *   **Testing:** Write a unit test for `run_pipeline` and an integration test for the `pipelines/run` tool.
    *   **Documentation:** Add docstrings for the method and tool.

*   [x] **Feature: Get Pipeline Run Status**
    *   **Functionality:** Implement `get_pipeline_run` in `ado/client.py` using the [runs get](https://learn.microsoft.com/en-us/rest/api/azure/devops/pipelines/runs/get?view=azure-devops-rest-7.2) API.
    *   **Tooling:** Create a `pipelines/runs/get` tool in `ado/tools.py`.
    *   **Testing:** Write a unit test for `get_pipeline_run` and an integration test for the `pipelines/runs/get` tool.
    *   **Documentation:** Add docstrings for the method and tool.

*   [x] **Feature: Pipeline Preview** - 2025-07-13
    *   **Functionality:** Implement `preview_pipeline` in `ado/client.py` using the [pipeline preview](https://learn.microsoft.com/en-us/rest/api/azure/devops/pipelines/preview/preview?view=azure-devops-rest-7.2) API.
    *   **Models:** Added `PipelinePreviewRequest` and `PreviewRun` models to handle preview request parameters and response data.
    *   **Tooling:** Created `preview_pipeline` tool in `ado/tools.py` with support for yamlOverride, variables, templateParameters, and stagesToSkip.
    *   **Testing:** Added comprehensive tests for static preview, parameterized pipelines, YAML override, error handling, and edge cases.
    *   **Test Infrastructure:** Created 3 dedicated test pipelines for preview testing:
        - preview-test-valid (ID: 74) - Simple valid pipeline
        - preview-test-parameterized (ID: 75) - Pipeline with parameters and variables
        - preview-test-invalid (ID: 76) - Pipeline with intentional errors for error testing
    *   **Test Fixtures:** Added test YAML files: valid-preview.yml, parameterized-preview.yml, invalid-preview.yml
    *   **Documentation:** Added Google-style docstrings for all public methods and tools.

*   [ ] **Feature: Get Pipeline Logs**
    *   **Functionality:** Implement `list_pipeline_logs` and `get_pipeline_log_content` in `ado/client.py` using the [logs list](https://learn.microsoft.com/en-us/rest/api/azure/devops/pipelines/logs/list?view=azure-devops-rest-7.2) and [logs get](https://learn.microsoft.com/en-us/rest/api/azure/devops/pipelines/logs/get?view=azure-devops-rest-7.2) APIs.
    *   **Tooling:** Create `pipelines/logs/list` and `pipelines/logs/get` tools in `ado/tools.py`.
    *   **Testing:** Write unit tests for both log methods and integration tests for both log tools.
    *   **Documentation:** Add docstrings for the methods and tools.

## Discovered During Work

*   [x] **Feature: Comprehensive Pipeline E2E Tests** - 2025-07-13
    *   **Enhanced Models:** Added `RunState`, `RunResult` enums and `PipelineReference` model with helper methods
    *   **Enhanced Client:** Updated `run_pipeline` and `get_pipeline_run` to return structured `PipelineRun` objects
    *   **Wait for Completion:** Added `wait_for_pipeline_completion` method with polling and timeout
    *   **Comprehensive Tests:** Created fire-and-forget, wait-for-completion, multiple runs, and status progression tests
    *   **Test Infrastructure:** Added `task test-single` command and updated CLAUDE.md with testing guidelines
    *   **FastMCP Integration:** Tests properly handle dictionary responses from FastMCP transport layer
    *   **API Fix:** Fixed `get_pipeline_run` endpoint to use correct Azure DevOps API format: `/pipelines/{pipelineId}/runs/{runId}`
    *   **Dedicated Test Pipelines:** Created 5 dedicated pipelines for run_pipeline tests to eliminate create/delete overhead:
        - test_run_and_get_pipeline_run_details (ID: 59)
        - test_pipeline_lifecycle_fire_and_forget (ID: 60)
        - test_pipeline_lifecycle_wait_for_completion (ID: 61)
        - test_multiple_pipeline_runs (ID: 62)
        - test_pipeline_run_status_progression (ID: 63)
    *   **Parallel Test Execution:** Added pytest-xdist for 5.5x faster test execution (~15s vs 80s):
        - `task test` runs tests in parallel by default
        - `task test-sequential` for debugging when sequential execution is needed
        - `task coverage` also supports parallel execution