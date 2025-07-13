k

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

### 6.1. Model Context Protocol (MCP) Architecture

This server will function as an MCP Server, enabling seamless communication between LLM applications (Hosts/Clients) and Azure DevOps. It will adhere to the MCP client-server architecture, providing context and tools to MCP Clients.

*   **Transport Layer:** The server will primarily use **Stdio transport** for communication, leveraging standard input/output. This is ideal for local processes and efficient for same-machine communication.
*   **Protocol Layer:** Communication will follow the **JSON-RPC 2.0** specification for message exchange, including:
    *   **Requests:** Expect a response from the client (e.g., `pipelines/list`).
    *   **Results:** Successful responses to requests.
    *   **Errors:** Indicate that a request failed, with defined error codes.
    *   **Notifications:** One-way messages that do not expect a response.
*   **Connection Lifecycle:** The server will manage the standard MCP connection lifecycle: Initialization (client sends `initialize`, server responds, client sends `initialized`), Message Exchange (Request-Response, Notifications), and Termination (clean shutdown or error conditions).

### 6.2. General Design Principles

*   The server will be designed as a conversational MCP server, following the best practices of modern MCP servers.
*   The interaction between the AI and the server will be through a well-defined API that is easy for the AI to understand and use.

## 7. Technical Considerations

*   The server will be built using Python and leverage the `mcp` Python SDK.
*   The server will use the Azure DevOps REST API to interact with ADO.
*   The server will need to securely store and manage the Azure DevOps Personal Access Token (`AZURE_DEVOPS_EXT_PAT`).

## 8. Best Practices and Security Considerations (MCP Specific)

*   **Transport Security:** For `stdio` transport, security is inherently managed by the local process environment. If remote communication is considered in the future, TLS and authentication will be critical.
*   **Message Validation:** All incoming MCP messages will be thoroughly validated, and inputs will be sanitized to prevent injection risks.
*   **Error Handling:** Errors will be handled gracefully, using appropriate MCP error codes, providing helpful messages, and ensuring sensitive information is not leaked.
*   **Resource Protection:** Access controls will be implemented for Azure DevOps resources, and requests will be rate-limited if necessary.

## 8.1 User Journeys

Human asks to execute a pipeline by name
1. AI lists pipelines using the list pipelines tool
2. The list pipelines tool gives the ID of the pipeline as part of the output
3. The AI uses the run pipelines tool to execute the pipeline by id
4. The run pipelines tool outputs a URL to the running pipeline the AI provides to the user

Human asks to execute a pipeline but gives a name that doesn't exist 
1. AI lists pipelines using the list pipelines tool
2. No pipeline shows up in the list matching the name, or anywhere close to it.
3. The AI gets some pipeline names that are the closest to what they ask, and asks if it is one of those or in a different project.

Human asks the AI to investigate a pipeline URL that they say has failed
1. AI uses the URL to extract the appropriate info to use the List Pipeline Run Logs tool
2. The tools gives log information that can be used to find the error message logs using the Get Pipeline Run Logs tool
2. The Run Logs tool gives the error message from the pipeline which the AI analyzes the error message and summarizes and gives potential solution

Human asks the AI to trigger a pipeline and asks them to let them know when it is finished
1. AI lists pipelines using the list pipelines tool
2. The list pipelines tool gives the ID of the pipeline as part of the output
3. The AI uses the run pipelines tool to execute the pipeline by id
4. The AI waits a minute and then checks the pipeline using the pipeline runs get
5. The run state is in progress, so the AI waits again 1 minute
6. The AI uses pipeline runs get tool to check the status of the running pipeline
7. The running pipeline is completed, but failed
8. The AI gives the human the error message for the pipeline and then offers a potential fix after inspecting the pipeline yaml.

## 8.2 Azure DevOps APIs we will need to implement

1. [projects list](https://learn.microsoft.com/en-us/rest/api/azure/devops/core/projects/list?view=azure-devops-rest-7.2&tabs=HTTP)
2. [projects get](https://learn.microsoft.com/en-us/rest/api/azure/devops/core/projects/get?view=azure-devops-rest-7.2)
1. [pipelines list](https://learn.microsoft.com/en-us/rest/api/azure/devops/pipelines/pipelines/list?view=azure-devops-rest-7.2)
2. [pipelines get](https://learn.microsoft.com/en-us/rest/api/azure/devops/pipelines/pipelines/get?view=azure-devops-rest-7.2)
3. [pipelines create](https://learn.microsoft.com/en-us/rest/api/azure/devops/pipelines/pipelines/create?view=azure-devops-rest-7.2)
3. [pipelines runs list](https://learn.microsoft.com/en-us/rest/api/azure/devops/pipelines/runs/list?view=azure-devops-rest-7.2)
4. [pipelines runs get](https://learn.microsoft.com/en-us/rest/api/azure/devops/pipelines/runs/get?view=azure-devops-rest-7.2)
5. [pipelines runs run pipeline](https://learn.microsoft.com/en-us/rest/api/azure/devops/pipelines/runs/run-pipeline?view=azure-devops-rest-7.2)
6. [pipelines logs list](https://learn.microsoft.com/en-us/rest/api/azure/devops/pipelines/logs/list?view=azure-devops-rest-7.2)
7. [pipelines logs get](https://learn.microsoft.com/en-us/rest/api/azure/devops/pipelines/logs/get?view=azure-devops-rest-7.2)

## 9. Success Metrics

*   The AI can successfully run a pipeline and report on its status.
*   The AI can successfully retrieve logs from a failed pipeline and provide a helpful summary of the error.
*   The time it takes for a user to resolve a pipeline issue is reduced.

## 9. Open Questions

*   How should the server handle long-running pipelines? What is the timeout for polling?
*   How should the PAT be provided to the server? Via an environment variable, a configuration file, or another method?
