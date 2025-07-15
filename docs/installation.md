# Installation

## Prerequisites

You'll need these installed before setting up the MCP server:

### 1. UV (Python package runner)

```bash
# Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Azure CLI with DevOps extension

```bash
# Install Azure CLI
# macOS: brew install azure-cli
# Windows: winget install Microsoft.AzureCLI
# Linux: curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Install Azure DevOps extension
az extension add --name azure-devops
```

### 3. Authenticate with Azure DevOps

```bash
# Login to Azure DevOps with your PAT
az devops login --organization https://dev.azure.com/YourOrg
```

When prompted, enter your Personal Access Token. This stores your credentials securely in the system keyring.

### 4. Test the setup

```bash
# Test that everything works
uvx ado-mcp-raboley --help
```

## IDE Integration

### Claude Desktop

**macOS Configuration** (`~/Library/Application Support/Claude/claude_desktop_config.json`):
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

**Windows Configuration** (`%APPDATA%\Claude\claude_desktop_config.json`):
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

### Claude Code

```bash
# Add to local scope (project-specific)
claude mcp add ado-mcp uvx ado-mcp-raboley -e ADO_ORGANIZATION_URL=https://dev.azure.com/YourOrg

# Or add to user scope (available across all projects)
claude mcp add ado-mcp uvx ado-mcp-raboley -e ADO_ORGANIZATION_URL=https://dev.azure.com/YourOrg -s user
```

### Cursor

1. Go to: `Settings` → `Cursor Settings` → `MCP` → `Add new global MCP server`
2. Configuration:
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

### VS Code with Continue

1. Install Continue extension from VS Code marketplace
2. Configure in `~/.continue/config.json`:
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

### Zed

1. Open Zed settings (`Cmd+,` on macOS, `Ctrl+,` on Linux/Windows)
2. Add to MCP settings:
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

## Alternative Authentication

If you prefer not to use Azure CLI, you can set environment variables directly:

```bash
export AZURE_DEVOPS_EXT_PAT="your-personal-access-token"
export ADO_ORGANIZATION_URL="https://dev.azure.com/YourOrg"
```

**⚠️ Security Note**: This method requires storing tokens as environment variables. The Azure CLI method is more secure as it stores credentials in the system keyring.