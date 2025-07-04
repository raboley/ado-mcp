# Product Requirements Document: Azure DevOps MCP Server

## 1. Introduction/Overview

This document outlines the requirements for an Azure DevOps (ADO) Model Context Protocol (MCP) Server. This server will enable a Gemini AI assistant to interact with Azure DevOps to execute and monitor pipelines. The primary goal is to create a seamless experience for the AI to manage ADO pipelines, retrieve results, and use those results to assist users or for its own learning and problem-solving. This will shorten the development loop by allowing the AI to identify and potentially fix issues in ADO pipelines without human intervention.

## 2. Goals

*   **Automation:** Enable the AI to programmatically run ADO pipelines.
*   **Efficiency:** Reduce the need for human intervention in the pipeline execution and debugging process.
*   **Intelligence:** Allow the AI to learn from pipeline failures and provide intelligent suggestions for fixes.
*   **User Experience:** Create a conversational and intuitive interface for the AI to interact with the ADO server.

## 3. User Stories

*   As an AI assistant, I want to be able to list all available pipelines in a given ADO organization and project so that I can help the user choose the correct one.
*   As an AI assistant, I want to be able to inspect a pipeline to see its required and optional parameters, so that I can guide the user in providing the correct inputs.
*   As an AI assistant, I want to be able to run a pipeline with a given set of parameters.
*   As an AI assistant, I want to be notified when a pipeline has completed, and whether it succeeded or failed.
*   As an AI assistant, when a pipeline fails, I want to retrieve the full logs so that I can analyze them and provide a helpful summary of the error to the user.
*   As an AI assistant, I want to be able to view the history of previously run pipelines to understand past successes and failures.

## 4. Functional Requirements

1.  The server MUST provide an endpoint to list all pipelines within a specified ADO organization and project.
2.  The server MUST provide an endpoint to get the details of a specific pipeline, including its parameters (name, type, default value, required/optional).
3.  The server MUST provide an endpoint to trigger a pipeline run with specified parameters.
4.  The server MUST provide an endpoint to get the status of a pipeline run (e.g., in progress, succeeded, failed).
5.  The server MUST poll for the status of a pipeline run and provide a final success/failure notification.
6.  The server MUST provide an endpoint to retrieve the full logs for a completed pipeline run.
7.  The server MUST use a Personal Access Token (PAT) for authentication with the Azure DevOps API.
8.  The server SHOULD be able to identify and suggest similar pipeline names if an exact match is not found.
9.  The server SHOULD provide helpful error messages if a user provides incorrect or missing parameters.

## 5. Non-Goals (Out of Scope)

*   The server will not manage ADO projects, teams, or users.
*   The server will not create or modify pipeline definitions.
*   The server will not support any authentication methods other than PAT.

## 6. Design Considerations

*   The server will be designed as a conversational MCP server, following the best practices of other modern MCP servers.
*   The interaction between the AI and the server will be through a well-defined API that is easy for the AI to understand and use.

## 7. Technical Considerations

*   The server will be built using Python.
*   The server will use the Azure DevOps REST API to interact with ADO.
*   The server will need to securely store and manage the ADO Personal Access Token.

## 8. Success Metrics

*   The AI can successfully run a pipeline and report on its status.
*   The AI can successfully retrieve logs from a failed pipeline and provide a helpful summary of the error.
*   The time it takes for a user to resolve a pipeline issue is reduced.

## 9. Open Questions

*   How should the server handle long-running pipelines? What is the timeout for polling?
*   How should the PAT be provided to the server? Via an environment variable, a configuration file, or another method?
