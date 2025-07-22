# ADO MCP

An MCP (Model Context Protocol) server that provides Azure DevOps integration for AI assistants and development tools. Enables your AI assistant to list projects, run pipelines, analyze failures, view logs, and troubleshoot builds directly from your chat interface.

📚 **[Full Documentation](https://ado-mcp.readthedocs.io/)** | 🚀 **[Quick Start](#prerequisites)** | 🛠️ **[API Reference](https://ado-mcp.readthedocs.io/en/latest/api.html)**

## Prerequisites

You'll need these installed before setting up the MCP server:

1. **UV** (Python package runner):
   ```bash
   # Install UV (if not already installed)
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Azure CLI with DevOps extension**:
   ```bash
   # Install Azure CLI
   # macOS: brew install azure-cli
   # Windows: winget install Microsoft.AzureCLI
   # Linux: curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
   
   # Install Azure DevOps extension
   az extension add --name azure-devops
   ```

3. **Authenticate with Azure DevOps**:
   ```bash
   # Login to Azure DevOps with your PAT
   az devops login --organization https://dev.azure.com/YourOrg
   ```
   
   When prompted, enter your Personal Access Token. This stores your credentials securely in the system keyring.

4. **Test the setup**:
   ```bash
   # Test that everything works
   uvx ado-mcp-raboley --help
   ```

## Installation

<details>
<summary><b>Install in Claude Desktop</b></summary>

1. **macOS Configuration** (`~/Library/Application Support/Claude/claude_desktop_config.json`):
   ```json
   {
     "mcpServers": {
       "ado-mcp": {
         "command": "uvx",
         "args": ["ado-mcp-raboley"],
         "env": {
           "ADO_ORGANIZATION_URL": "https://dev.azure.com/YourOrg"
         }
       }
     }
   }
   ```

2. **Windows Configuration** (`%APPDATA%\Claude\claude_desktop_config.json`):
   ```json
   {
     "mcpServers": {
       "ado-mcp": {
         "command": "uvx",
         "args": ["ado-mcp-raboley"],
         "env": {
           "ADO_ORGANIZATION_URL": "https://dev.azure.com/YourOrg"
         }
       }
     }
   }
   ```

3. **Restart Claude Desktop** to load the MCP server.

**Note**: `uvx` automatically downloads and runs the latest version. No manual installation needed!

</details>

<details>
<summary><b>Install in Claude Code</b></summary>

1. **Add the MCP server**:
   ```bash
   # Add to local scope (project-specific)
   claude mcp add ado-mcp uvx ado-mcp-raboley -e ADO_ORGANIZATION_URL=https://dev.azure.com/YourOrg
   
   # Or add to user scope (available across all projects)
   claude mcp add ado-mcp uvx ado-mcp-raboley -e ADO_ORGANIZATION_URL=https://dev.azure.com/YourOrg -s user
   ```

2. **Verify the installation**:
   ```bash
   # List configured MCP servers
   claude mcp list
   ```

3. **Use in Claude Code**:
   - Reference Azure DevOps resources with `@ado-mcp:...`
   - Use slash commands like `/mcp__ado-mcp__list_projects`
   - Ask Claude to interact with your Azure DevOps pipelines directly

**Note**: Claude Code automatically handles the `uvx` execution and authentication via Azure CLI.

</details>

<details>
<summary><b>Install in Cursor</b></summary>

1. Go to: `Settings` → `Cursor Settings` → `MCP` → `Add new global MCP server`

2. **Configuration**:
   ```json
   {
     "name": "ado-mcp",
     "command": "uvx",
     "args": ["ado-mcp-raboley"],
     "env": {
       "ADO_ORGANIZATION_URL": "https://dev.azure.com/YourOrg"
     }
   }
   ```

3. **Save** and restart Cursor.

</details>

<details>
<summary><b>Install in VS Code with Continue</b></summary>

1. **Install Continue extension** from VS Code marketplace.

2. **Configure in `~/.continue/config.json`**:
   ```json
   {
     "models": [...],
     "mcpServers": [
       {
         "name": "ado-mcp",
         "command": "uvx",
         "args": ["ado-mcp-raboley"],
         "env": {
           "ADO_ORGANIZATION_URL": "https://dev.azure.com/YourOrg"
         }
       }
     ]
   }
   ```

3. **Restart VS Code** to load the configuration.

</details>

<details>
<summary><b>Install in Zed</b></summary>

1. **Open Zed settings** (`Cmd+,` on macOS, `Ctrl+,` on Linux/Windows).

2. **Add to MCP settings**:
   ```json
   {
     "language_models": {
       "mcp_servers": {
         "ado-mcp": {
           "command": "uvx",
           "args": ["ado-mcp-raboley"],
           "env": {
             "ADO_ORGANIZATION_URL": "https://dev.azure.com/YourOrg"
           }
         }
       }
     }
   }
   ```

3. **Restart Zed** to apply changes.

</details>

<details>
<summary><b>Install in any MCP-compatible client</b></summary>

The server can be used with any MCP-compatible client:

**Command**: `uvx ado-mcp-raboley`

**Required environment variable**:
- `ADO_ORGANIZATION_URL`: Your Azure DevOps organization URL (e.g., `https://dev.azure.com/YourOrg`)

**Connection details**:
- **Protocol**: stdio
- **Capabilities**: Tools, Resources
- **Transport**: Standard input/output

**Authentication**: Automatically uses Azure CLI credentials from `az devops login`

</details>

<details>
<summary><b>Alternative: Environment Variable Authentication</b></summary>

If you prefer not to use Azure CLI, you can set environment variables directly:

1. **Set environment variables**:
   ```bash
   export AZURE_DEVOPS_EXT_PAT="your-personal-access-token"
   export ADO_ORGANIZATION_URL="https://dev.azure.com/YourOrg"
   ```

2. **Configure with environment variables**:
   ```json
   {
     "mcpServers": {
       "ado-mcp": {
         "command": "uvx",
         "args": ["ado-mcp-raboley"]
       }
     }
   }
   ```

**⚠️ Security Note**: This method requires storing tokens as environment variables. The Azure CLI method is more secure as it stores credentials in the system keyring.

</details>

## Features

### 🔧 Pipeline Operations
- **List and manage pipelines** - View all pipelines in your Azure DevOps projects
- **Run pipelines** - Trigger pipeline execution with real-time status monitoring
- **Pipeline analysis** - Get detailed failure summaries, logs, and timeline analysis
- **Build management** - Track build results and access build artifacts

### 🔍 Smart Search & Discovery
- **Name-based lookups** - Find projects and pipelines using fuzzy matching
- **URL parsing** - Extract pipeline information from Azure DevOps web URLs
- **Project exploration** - Browse available projects and their pipelines

### 📊 Logs & Debugging
- **Failure analysis** - Intelligent root cause analysis for failed pipelines
- **Step-by-step logs** - Access detailed logs for individual pipeline steps
- **Timeline visualization** - See execution flow and timing information
- **Log filtering** - Search and filter logs by step name or content

### 🔐 Flexible Authentication
- **Personal Access Tokens** - Traditional PAT-based authentication
- **Azure CLI integration** - Seamless integration with existing Azure CLI sessions
- **Multiple auth fallbacks** - Automatic fallback between authentication methods

### ⚡ Performance & Caching
- **Intelligent caching** - Fast project and pipeline lookups with automatic cache invalidation
- **Batch operations** - Efficient handling of multiple requests
- **Resource optimization** - MCP resources for commonly accessed data

## Development Setup

1.  **Install Dependencies**:
    ```bash
    task install
    ```

2.  **Set up Authentication**:
    The MCP server supports multiple authentication methods (in order of precedence):

    ### Option 1: Personal Access Token (PAT)
    
    **Environment Variable Method:**
    ```bash
    task setup-env
    ```
    This creates a `.env` file with your Personal Access Token (PAT) and other necessary variables.

    **Direct Configuration:**
    ```bash
    export AZURE_DEVOPS_EXT_PAT="your-personal-access-token"
    export ADO_ORGANIZATION_URL="https://dev.azure.com/YourOrg"
    ```

    ### Option 2: Azure CLI Authentication (Recommended)
    
    If you already use Azure CLI, you can authenticate using your existing session:
    
    ```bash
    # Login to Azure (if not already logged in)
    az login
    
    # The MCP server will automatically use your Azure CLI credentials
    task run
    ```
    
    **Benefits of Azure CLI authentication:**
    - No need to manage Personal Access Tokens
    - Uses your existing Azure credentials 
    - More secure than storing PATs
    - Automatically refreshes tokens
    
    **Note:** Azure CLI authentication requires the user to be logged in with an account that has access to the Azure DevOps organization.

## Testing

The ado-mcp project uses a Terraform-based test infrastructure that creates isolated test environments.

### Quick Test Setup

1. **Configure environment**:
   ```bash
   cp .env.example .env  # Edit with your Azure DevOps details
   ```

2. **Provision test environment**:
   ```bash
   task ado-up  # Creates Azure DevOps project and infrastructure
   ```

3. **Run tests**:
   ```bash
   task test
   ```

4. **Clean up**:
   ```bash
   task ado-down  # Destroys the test environment
   ```

### Test Commands

-   **Run all tests** (parallel):
    ```bash
    task test
    ```

-   **Run single test**:
    ```bash
    task test-single TEST_NAME=tests/test_example.py::test_function_name
    ```

-   **Test coverage**:
    ```bash
    task coverage
    ```

📚 **[Detailed Testing Setup Guide](docs/TESTING_SETUP.md)**

-   **Setup Azure DevOps CLI** (for Azure DevOps CLI commands):
    ```bash
    task setup-ado-cli
    ```
    This will:
    - Install Azure CLI if needed
    - Install Azure DevOps CLI extension if needed
    - Login to Azure DevOps CLI using your PAT (from AZURE_DEVOPS_EXT_PAT)
    - Configure default organization and project
    
    **Note**: This is for `az devops` commands and does NOT enable the Azure CLI authentication test, which requires full Azure authentication (`az login`).

## Usage

-   **Run the MCP Server**:
    ```bash
    task run
    ```

-   **Inspect the MCP Server**:
    ```bash
    task inspect
    ```

## Getting Started

Once installed and configured, you can use the MCP server through your AI assistant. Here are some common tasks:

### Basic Operations

**List all projects:**
```
Show me all Azure DevOps projects in my organization.
```

**Find and run a pipeline:**
```
Find the "deploy-production" pipeline in the "MyApp" project and run it.
```

**Check recent build failures:**
```
What pipelines have failed recently? Show me the failure details.
```

### Pipeline Analysis

**Analyze a failed build from a URL:**
```
Analyze this failed build: https://dev.azure.com/MyOrg/MyProject/_build/results?buildId=123
```

**Get detailed failure logs:**
```
Show me the detailed logs for the failed steps in pipeline run 456.
```

**Compare pipeline runs:**
```
Compare the latest run of "ci-pipeline" with the previous successful run.
```

### Advanced Usage

**Monitor pipeline execution:**
```
Run the "integration-tests" pipeline and monitor its progress. Alert me when it completes.
```

**Create deployment insights:**
```
Generate a summary of all deployment pipeline runs from the last week.
```

**Troubleshoot build issues:**
```
Help me troubleshoot why the "build-and-test" pipeline keeps failing on the test step.
```

## Troubleshooting

### Authentication Issues

**"No authentication method available" error:**
```bash
# Check if you're logged into Azure DevOps
az devops configure --list

# If not configured, login with your PAT
az devops login --organization https://dev.azure.com/YourOrg
```

**"Authentication failed" with sign-in page response:**
```bash
# Your PAT might be expired, login again
az devops logout
az devops login --organization https://dev.azure.com/YourOrg
```

**Permission errors:**
- Ensure your PAT has the following scopes:
  - **Build**: Read & execute
  - **Project and team**: Read
  - **Release**: Read, write, & execute
  - **Code**: Read (if accessing repositories)

### Installation Issues

**"uvx ado-mcp-raboley" not working:**
```bash
# Check UV installation
uvx --version

# Install UV if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Test the package
uvx ado-mcp-raboley --help
```

**Azure CLI not found:**
```bash
# Install Azure CLI (Ubuntu/Debian)
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Install Azure CLI (macOS)
brew install azure-cli

# Install Azure CLI (Windows)
# Download and install from: https://aka.ms/installazurecliwindows
```

---

## Development Setup

If you want to contribute to this project or run it from source:

1.  **Install Dependencies**:
    ```bash
    task install
    ```

2.  **Set up Authentication**:
    The MCP server supports multiple authentication methods (in order of precedence):

    ### Option 1: Personal Access Token (PAT)
    
    **Environment Variable Method:**
    ```bash
    task setup-env
    ```
    This creates a `.env` file with your Personal Access Token (PAT) and other necessary variables.

    **Direct Configuration:**
    ```bash
    export AZURE_DEVOPS_EXT_PAT="your-personal-access-token"
    export ADO_ORGANIZATION_URL="https://dev.azure.com/YourOrg"
    ```

    ### Option 2: Azure CLI Authentication (Recommended)
    
    If you already use Azure CLI, you can authenticate using your existing session:
    
    ```bash
    # Login to Azure (if not already logged in)
    az login
    
    # The MCP server will automatically use your Azure CLI credentials
    task run
    ```
    
    **Benefits of Azure CLI authentication:**
    - No need to manage Personal Access Tokens
    - Uses your existing Azure credentials 
    - More secure than storing PATs
    - Automatically refreshes tokens
    
    **Note:** Azure CLI authentication requires the user to be logged in with an account that has access to the Azure DevOps organization.

## Testing

The ado-mcp project uses a Terraform-based test infrastructure that creates isolated test environments.

### Quick Test Setup

1. **Configure environment**:
   ```bash
   cp .env.example .env  # Edit with your Azure DevOps details
   ```

2. **Provision test environment**:
   ```bash
   task ado-up  # Creates Azure DevOps project and infrastructure
   ```

3. **Run tests**:
   ```bash
   task test
   ```

4. **Clean up**:
   ```bash
   task ado-down  # Destroys the test environment
   ```

### Test Commands

-   **Run all tests** (parallel):
    ```bash
    task test
    ```

-   **Run single test**:
    ```bash
    task test-single TEST_NAME=tests/test_example.py::test_function_name
    ```

-   **Test coverage**:
    ```bash
    task coverage
    ```

📚 **[Detailed Testing Setup Guide](docs/TESTING_SETUP.md)**

-   **Setup Azure DevOps CLI** (for Azure DevOps CLI commands):
    ```bash
    task setup-ado-cli
    ```
    This will:
    - Install Azure CLI if needed
    - Install Azure DevOps CLI extension if needed
    - Login to Azure DevOps CLI using your PAT (from AZURE_DEVOPS_EXT_PAT)
    - Configure default organization and project
    
    **Note**: This is for `az devops` commands and does NOT enable the Azure CLI authentication test, which requires full Azure authentication (`az login`).

## Usage

-   **Run the MCP Server**:
    ```bash
    task run
    ```

-   **Inspect the MCP Server**:
    ```bash
    task inspect
    ```

## Documentation

-   **View documentation locally**:
    ```bash
    task docs-serve
    ```
    
    This automatically builds the docs and serves them at http://localhost:8000

The documentation is built with [Sphinx](https://www.sphinx-doc.org/) and hosted on [Read the Docs](https://ado-mcp.readthedocs.io/).

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