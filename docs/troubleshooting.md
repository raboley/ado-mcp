# Troubleshooting

This guide helps you resolve common issues with ADO MCP.

## Authentication Issues

### "No authentication method available" Error

**Symptoms**: The MCP server fails to start with authentication errors.

**Solutions**:

1. **Check Azure DevOps login status**:
   ```bash
   az devops configure --list
   ```

2. **Login if not configured**:
   ```bash
   az devops login --organization https://dev.azure.com/YourOrg
   ```

3. **Verify environment variables** (if using PAT):
   ```bash
   echo $AZURE_DEVOPS_EXT_PAT
   echo $ADO_ORGANIZATION_URL
   ```

### "Authentication failed" with Sign-in Page Response

**Symptoms**: Authentication appears to work but API calls return HTML sign-in pages.

**Causes**: 
- Expired Personal Access Token
- Invalid token scopes
- Organization policy restrictions

**Solutions**:

1. **Refresh your authentication**:
   ```bash
   az devops logout
   az devops login --organization https://dev.azure.com/YourOrg
   ```

2. **Check PAT scopes** (if using PAT directly):
   - **Build**: Read & execute
   - **Project and team**: Read
   - **Release**: Read, write, & execute
   - **Code**: Read (if accessing repositories)

3. **Verify organization URL format**:
   ```bash
   # Correct format
   https://dev.azure.com/YourOrganization
   
   # Not this
   https://YourOrganization.visualstudio.com
   ```

### Microsoft Entra Token Issues

**Symptoms**: Azure CLI authentication works but gives sign-in page responses.

**Cause**: Some Azure DevOps organizations don't accept Microsoft Entra tokens for API access.

**Solution**: Use Personal Access Token authentication instead:

```bash
export AZURE_DEVOPS_EXT_PAT="your-personal-access-token"
export ADO_ORGANIZATION_URL="https://dev.azure.com/YourOrg"
```

## Installation Issues

### "uvx ado-mcp-raboley" Not Working

**Symptoms**: Command not found or execution errors.

**Solutions**:

1. **Check UV installation**:
   ```bash
   uvx --version
   ```

2. **Install UV if needed**:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   source ~/.bashrc  # or restart terminal
   ```

3. **Test package directly**:
   ```bash
   uvx ado-mcp-raboley --help
   ```

4. **Clear UV cache if needed**:
   ```bash
   uv cache clean
   ```

### Azure CLI Not Found

**Symptoms**: `az` command not found or Azure DevOps extension missing.

**Solutions**:

1. **Install Azure CLI**:
   ```bash
   # Ubuntu/Debian
   curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
   
   # macOS
   brew install azure-cli
   
   # Windows
   winget install Microsoft.AzureCLI
   ```

2. **Install Azure DevOps extension**:
   ```bash
   az extension add --name azure-devops
   ```

3. **Verify installation**:
   ```bash
   az --version
   az extension list | grep azure-devops
   ```

## Runtime Issues

### Slow Performance

**Symptoms**: MCP operations take a long time to complete.

**Causes**: Network issues, large organizations, or cache misses.

**Solutions**:

1. **Check cache status** (through AI assistant):
   ```
   "Show me the cache statistics for the MCP server"
   ```

2. **Warm up cache**:
   ```
   "List all projects"  # This caches project data
   "List pipelines in MyProject"  # This caches pipeline data
   ```

3. **Use specific queries**:
   ```
   # Instead of
   "Show me all pipeline runs"
   
   # Use
   "Show me pipeline runs for 'specific-pipeline' in 'MyProject'"
   ```

### Connection Timeouts

**Symptoms**: Operations fail with timeout errors.

**Solutions**:

1. **Check network connectivity**:
   ```bash
   curl -I https://dev.azure.com/YourOrg
   ```

2. **Verify organization URL**:
   ```bash
   az devops configure --list
   ```

3. **Test with shorter operations**:
   ```
   "List projects"  # Simple operation to test connectivity
   ```

## MCP Client Issues

### Claude Desktop Not Loading Server

**Symptoms**: MCP server doesn't appear in Claude Desktop.

**Solutions**:

1. **Check configuration file location**:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`

2. **Validate JSON syntax**:
   ```bash
   # Use a JSON validator or
   python -m json.tool claude_desktop_config.json
   ```

3. **Check configuration format**:
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

4. **Restart Claude Desktop** completely.

### Server Not Responding

**Symptoms**: MCP server starts but doesn't respond to requests.

**Solutions**:

1. **Test server directly**:
   ```bash
   uvx ado-mcp-raboley
   # Should start and show MCP server output
   ```

2. **Check environment variables**:
   ```bash
   env | grep ADO
   env | grep AZURE
   ```

3. **Enable debug logging** (if available):
   ```json
   {
     "mcpServers": {
       "ado-mcp": {
         "command": "uvx",
         "args": ["ado-mcp-raboley"],
         "env": {
           "ADO_ORGANIZATION_URL": "https://dev.azure.com/YourOrg",
           "DEBUG": "1"
         }
       }
     }
   }
   ```

## API and Data Issues

### "Project not found" Errors

**Symptoms**: Cannot find projects that exist in Azure DevOps.

**Solutions**:

1. **Check project permissions**:
   - Verify your account has access to the project
   - Check PAT scopes include "Project and team: Read"

2. **Use exact project names**:
   ```
   # Instead of partial names
   "Find project 'My'"
   
   # Use more specific names
   "Find project 'MyWebApplication'"
   ```

3. **List all projects first**:
   ```
   "List all projects I have access to"
   ```

### Pipeline Not Found

**Symptoms**: Pipelines exist but cannot be found by name.

**Solutions**:

1. **Use fuzzy matching**:
   ```
   # The system supports fuzzy matching
   "Find pipeline 'deploy' in 'MyProject'"  # Finds "deploy-production"
   ```

2. **Check pipeline permissions**:
   - Verify access to the specific pipeline
   - Check if pipeline is in a different project

3. **List pipelines first**:
   ```
   "List all pipelines in 'MyProject'"
   ```

## Getting Help

### Debug Information

When reporting issues, include:

1. **Version information**:
   ```bash
   uvx ado-mcp-raboley --version
   az --version
   uv --version
   ```

2. **Configuration** (sanitized):
   ```json
   {
     "mcpServers": {
       "ado-mcp": {
         "command": "uvx",
         "args": ["ado-mcp-raboley"],
         "env": {
           "ADO_ORGANIZATION_URL": "https://dev.azure.com/[REDACTED]"
         }
       }
     }
   }
   ```

3. **Error messages** (with sensitive information removed)

4. **Steps to reproduce** the issue

### Common Error Patterns

| Error Message | Likely Cause | Solution |
|---------------|--------------|----------|
| "Sign-in page" | Authentication issue | Refresh `az devops login` |
| "No authentication method" | Missing credentials | Set up Azure CLI or PAT |
| "Project not found" | Permissions or typo | Check access and spelling |
| "Command not found" | Installation issue | Install UV and Azure CLI |
| "Timeout" | Network or performance | Check connectivity and use specific queries |