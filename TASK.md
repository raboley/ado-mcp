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

*   [ ] **Feature: List ADO Pipelines**
    *   **Functionality:** Implement a `list_pipelines` method in `ado/client.py` to call the [pipelines list](https://learn.microsoft.com/en-us/rest/api/azure/devops/pipelines/pipelines/list?view=azure-devops-rest-7.2) API.
    *   **Tooling:** Create a `pipelines/list` tool in `ado/tools.py`.
    *   **Testing:** Write a unit test for `list_pipelines` and an integration test for the `pipelines/list` tool.
    *   **Documentation:** Add docstrings for the method and tool.

*   [ ] **Feature: Get Pipeline Details**
    *   **Functionality:** Implement `get_pipeline` in `ado/client.py` using the [pipelines get](https://learn.microsoft.com/en-us/rest/api/azure/devops/pipelines/pipelines/get?view=azure-devops-rest-7.2) API.
    *   **Tooling:** Create a `pipelines/get` tool in `ado/tools.py`.
    *   **Testing:** Write a unit test for `get_pipeline` and an integration test for the `pipelines/get` tool.
    *   **Documentation:** Add docstrings for the method and tool.

*   [ ] **Feature: Run a Pipeline**
    *   **Functionality:** Implement `run_pipeline` in `ado/client.py` using the [run pipeline](https://learn.microsoft.com/en-us/rest/api/azure/devops/pipelines/runs/run-pipeline?view=azure-devops-rest-7.2) API.
    *   **Tooling:** Create a `pipelines/run` tool in `ado/tools.py`.
    *   **Testing:** Write a unit test for `run_pipeline` and an integration test for the `pipelines/run` tool.
    *   **Documentation:** Add docstrings for the method and tool.

*   [ ] **Feature: Get Pipeline Run Status**
    *   **Functionality:** Implement `get_pipeline_run` in `ado/client.py` using the [runs get](https://learn.microsoft.com/en-us/rest/api/azure/devops/pipelines/runs/get?view=azure-devops-rest-7.2) API.
    *   **Tooling:** Create a `pipelines/runs/get` tool in `ado/tools.py`.
    *   **Testing:** Write a unit test for `get_pipeline_run` and an integration test for the `pipelines/runs/get` tool.
    *   **Documentation:** Add docstrings for the method and tool.

*   [ ] **Feature: Get Pipeline Logs**
    *   **Functionality:** Implement `list_pipeline_logs` and `get_pipeline_log_content` in `ado/client.py` using the [logs list](https://learn.microsoft.com/en-us/rest/api/azure/devops/pipelines/logs/list?view=azure-devops-rest-7.2) and [logs get](https://learn.microsoft.com/en-us/rest/api/azure/devops/pipelines/logs/get?view=azure-devops-rest-7.2) APIs.
    *   **Tooling:** Create `pipelines/logs/list` and `pipelines/logs/get` tools in `ado/tools.py`.
    *   **Testing:** Write unit tests for both log methods and integration tests for both log tools.
    *   **Documentation:** Add docstrings for the methods and tools.