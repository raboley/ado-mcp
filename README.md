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

## Working with Azure DevOps URLs

### Understanding Azure DevOps URL Structure

When working with Azure DevOps URLs from the web interface, it's important to understand the difference between **build/run IDs** and **pipeline definition IDs**:

**Example URL**: `https://dev.azure.com/RussellBoley/ado-mcp/_build/results?buildId=324&view=results`

- **Organization**: `RussellBoley` (from the URL path)
- **Project**: `ado-mcp` (from the URL path)
- **buildId=324**: This is a **run ID** (specific execution instance), NOT a pipeline definition ID

### Getting Pipeline Information from Build URLs

To work with a specific build/run from an Azure DevOps URL:

1. **Extract URL components**:
   - Organization: `RussellBoley`
   - Project: `ado-mcp` 
   - Build/Run ID: `324` (from `buildId` parameter)

2. **Use `get_build_by_id` to find the pipeline**:
   ```python
   # Get build details to find the pipeline definition
   build_details = await client.call_tool("get_build_by_id", {
       "project_id": "49e895da-15c6-4211-97df-65c547a59c22",  # ado-mcp project ID
       "build_id": 324  # The buildId from the URL
   })
   
   # Extract pipeline information
   pipeline_id = build_details.data["definition"]["id"]        # e.g., 84
   pipeline_name = build_details.data["definition"]["name"]    # e.g., "log-test-complex"
   ```

3. **Then use pipeline-specific tools**:
   ```python
   # Get detailed run information
   run_details = await client.call_tool("get_pipeline_run", {
       "project_id": "49e895da-15c6-4211-97df-65c547a59c22",
       "pipeline_id": pipeline_id,  # 84
       "run_id": 324               # Same as buildId
   })
   
   # Get failure analysis if needed
   failure_summary = await client.call_tool("get_pipeline_failure_summary", {
       "project_id": "49e895da-15c6-4211-97df-65c547a59c22",
       "pipeline_id": pipeline_id,
       "run_id": 324
   })
   ```

### Common Mistake to Avoid

❌ **Don't do this**: 
```python
# This will fail - you can't guess the pipeline_id
await client.call_tool("get_pipeline_run", {
    "project_id": "49e895da-15c6-4211-97df-65c547a59c22",
    "pipeline_id": 15,  # Wrong! This is just a guess
    "run_id": 324
})
```

✅ **Do this instead**:
```python
# First, get the build details to find the correct pipeline_id
build_data = await client.call_tool("get_build_by_id", {
    "project_id": "49e895da-15c6-4211-97df-65c547a59c22",
    "build_id": 324  # buildId from URL
})

pipeline_id = build_data.data["definition"]["id"]  # Now you have the correct pipeline_id

# Then use it for pipeline-specific operations
await client.call_tool("get_pipeline_run", {
    "project_id": "49e895da-15c6-4211-97df-65c547a59c22", 
    "pipeline_id": pipeline_id,  # Correct pipeline_id
    "run_id": 324
})
```

### Available Tools for Build/Pipeline Analysis

- **`get_build_by_id`**: Get build details and extract pipeline information from a build/run ID
- **`get_pipeline_run`**: Get detailed run information (requires both pipeline_id and run_id)
- **`get_pipeline_failure_summary`**: Analyze failures with root cause analysis
- **`get_failed_step_logs`**: Get logs for failed steps
- **`get_pipeline_timeline`**: Get execution timeline
- **`list_pipeline_logs`**: List all available logs
- **`get_log_content_by_id`**: Get specific log content
- **`run_pipeline_and_get_outcome`**: Run a pipeline and wait for completion with analysis 