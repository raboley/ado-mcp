# Task List: Azure DevOps MCP Server v0

This task list outlines the steps to get the initial version of the Azure DevOps MCP Server up and running.

## Sprint 1: Core Functionality

*   [x] Project Setup
    *   [x] Initialize a Python project with a virtual environment.
    *   [x] Add necessary dependencies to `pyproject.toml` (e.g., `fastapi`, `uvicorn`, `requests`).
    *   [x] Set up the basic project structure (e.g., `main.py`, `ado_client.py`).

*   **Task 2: ADO Client - Authentication**
    *   [ ] Implement a class to handle authentication with the Azure DevOps REST API using a Personal Access Token (PAT).
    *   [ ] The PAT should be configurable via an environment variable.

*   **Task 3: ADO Client - List Pipelines**
    *   [ ] Implement a function to list all pipelines in a given organization and project.
    *   [ ] Create a data model for the pipeline information.

*   **Task 4: API - List Pipelines**
    *   [ ] Create a FastAPI endpoint that exposes the "list pipelines" functionality.

## Sprint 2: Pipeline Execution

*   **Task 5: ADO Client - Get Pipeline Definition**
    *   [ ] Implement a function to get the detailed definition of a single pipeline, including its parameters.
    *   [ ] Create data models for the pipeline definition and parameters.

*   **Task 6: API - Get Pipeline Definition**
    *   [ ] Create a FastAPI endpoint that exposes the "get pipeline definition" functionality.

*   **Task 7: ADO Client - Run Pipeline**
    *   [ ] Implement a function to trigger a pipeline run with parameters.

*   **Task 8: API - Run Pipeline**
    *   [ ] Create a FastAPI endpoint that exposes the "run pipeline" functionality.

## Sprint 3: Pipeline Monitoring

*   **Task 9: ADO Client - Get Pipeline Run Status**
    *   [ ] Implement a function to get the status of a specific pipeline run.

*   **Task 10: API - Get Pipeline Run Status**
    *   [ ] Create a FastAPI endpoint that exposes the "get pipeline run status" functionality.

*   **Task 11: ADO Client - Get Pipeline Run Logs**
    *   [ ] Implement a function to retrieve the logs for a completed pipeline run.

*   **Task 12: API - Get Pipeline Run Logs**
    *   [ ] Create a FastAPI endpoint that exposes the "get pipeline run logs" functionality.

## Sprint 4: Observability and Documentation

*   **Task 13: Implement Logging**
    *   [ ] Add structured logging to the application.

*   **Task 14: AI-Consumable Documentation**
    *   [ ] Add docstrings to all functions and classes, explaining their purpose and usage.

*   **Task 15: End-to-End Tests**
    *   [ ] Write end-to-end tests for the entire workflow (list, get, run, status, logs).
    *   [ ] The tests should not use mocks and should interact with a real Azure DevOps project.

*   **Task 16: Commit and Finalize**
    *   [ ] Commit all changes with a clear and concise commit message.
