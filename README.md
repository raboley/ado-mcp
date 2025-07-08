# ADO MCP

This project uses [FastMCP 2.0](https://gofastmcp.com/getting-started/installation) python sdk to interact with Azure DevOps.

## Setup

1.  **Install Dependencies**:
    ```bash
    task install
    ```

2.  **Set up Environment Variables**:
    This project requires a `.env` file with your Azure DevOps credentials. You can create one by running:
    ```bash
    task setup-env
    ```
    This will create a `.env` file with your Personal Access Token (PAT) and other necessary variables.

## Testing

-   **Run Tests**:
    ```bash
    task test
    ```

-   **Test Coverage**:
    ```bash
    task coverage
    ```

## Usage

-   **Run the MCP Server**:
    ```bash
    task run
    ```

-   **Inspect the MCP Server**:
    ```bash
    task inspect
    ``` 