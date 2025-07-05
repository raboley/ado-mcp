# Task List: Azure DevOps MCP Server v0

This task list outlines the steps to get the initial version of the Azure DevOps MCP Server up and running.

## Sprint 1: Core Functionality

*   [x] Project Setup
    *   [x] Initialize a Python project with a virtual environment.
    *   [x] Add necessary dependencies to `pyproject.toml` (e.g., `fastapi`, `uvicorn`, `requests`).
    *   [x] Set up the basic project structure (e.g., `main.py`, `ado_client.py`).

*   [x] ADO Client - Authentication
    *   [x] Implement a class to handle authentication with the Azure DevOps REST API using a Personal Access Token (PAT).
    *   [x] The PAT should be configurable via an environment variable.
    *   [x] Add an authentication test to verify PAT functionality.
    *   [x] Add sad path test for missing PAT.

*   [x] ADO Client - List Pipelines
    *   [x] Implement a function to list all pipelines in a given organization and project.
    *   [x] Create a data model for the pipeline information.
    *   [x] Add end-to-end test for `list_pipelines` method (no mocks, with strong typing and count assertion).

*   [x] MCP Server - Setup
    *   [x] Initialize the MCP server using `mcp.server.fastmcp.FastMCP`.
    *   [x] Implement the main entry point to run the MCP server with `FastMCP.run()`.
    *   [x] Expose tools using the `@mcp.tool()` decorator.

*   **Task 5: MCP Server - List Pipelines**
    *   [x] Implement the `pipelines/list` MCP method to expose the "list pipelines" functionality.

## Sprint 2: Pipeline Execution

*   **Task 6: ADO Client - Get Pipeline Definition**
    *   [x] Implement a function to get the detailed definition of a single pipeline, including its parameters.
    *   [x] Create data models for the pipeline definition and parameters.

*   **Task 7: MCP Server - Get Pipeline Definition**
    *   [ ] Implement the `pipelines/get` MCP method to expose the "get pipeline definition" functionality.

*   **Task 8: ADO Client - Run Pipeline**
    *   [ ] Implement a function to trigger a pipeline run with parameters.

*   **Task 9: MCP Server - Run Pipeline**
    *   [ ] Implement the `pipelines/run` MCP method to expose the "run pipeline" functionality.

## Sprint 3: Pipeline Monitoring

*   **Task 10: ADO Client - Get Pipeline Run Status**
    *   [ ] Implement a function to get the status of a specific pipeline run.

*   **Task 11: MCP Server - Get Pipeline Run Status**
    *   [ ] Implement the `pipelines/status` MCP method to expose the "get pipeline run status" functionality.

*   **Task 12: ADO Client - Get Pipeline Run Logs**
    *   [ ] Implement a function to retrieve the logs for a completed pipeline run.

*   **Task 13: MCP Server - Get Pipeline Run Logs**
    *   [ ] Implement the `pipelines/logs` MCP method to expose the "get pipeline run logs" functionality.

## Sprint 4: Observability and Documentation

*   **Task 14: Implement Logging**
    *   [ ] Add structured logging to the application.

*   **Task 15: AI-Consumable Documentation**
    *   [ ] Add docstrings to all functions and classes, explaining their purpose and usage.

*   **Task 16: End-to-End Tests**
    *   [ ] Write end-to-end tests for the entire workflow (list, get, run, status, logs).
    *   [ ] The tests should not use mocks and should interact with a real Azure DevOps project.

*   **Task 17: Commit and Finalize**
    *   [ ] Commit all changes with a clear and concise commit message.
