# GitHub Service Connection Setup

This document explains how the GitHub service connection is automatically created via Terraform to support pipelines that use GitHub repository resources.

## Overview

The `github-resources-test-stable` pipeline and related tests require access to external GitHub repositories (specifically `raboley/tooling`). Azure DevOps requires a service connection to authenticate with GitHub for repository access during pipeline execution and preview.

## Automatic Setup via Terraform

The service connection is now created automatically via Terraform when you run:

```bash
task ado-up
```

## Prerequisites

1. **Azure DevOps Personal Access Token** (already configured in `.env`)
2. **GitHub Personal Access Token** with appropriate scopes

### GitHub Token Setup

1. Generate a GitHub Personal Access Token:
   - Go to https://github.com/settings/tokens
   - Click "Generate new token" → "Generate new token (classic)"
   - Select scopes:
     - `repo` (Full control of private repositories) - **Required for private repos**
     - `public_repo` (Access public repositories) - **Minimum for public repos**

2. Add the token to your `.env` file:
   ```bash
   GITHUB_TOKEN=your_github_token_here
   ```

## What Gets Created

Terraform creates a GitHub service endpoint with the name `raboley` that matches the endpoint name used in the pipeline YAML files:

```hcl
resource "azuredevops_serviceendpoint_github" "github_connection" {
  project_id                = var.project_id
  service_endpoint_name     = "raboley"  # Matches pipeline YAML
  description               = "GitHub service connection for testing repository resources"
  
  auth_personal {
    personal_access_token = var.github_token
  }
}
```

## Pipeline Integration

The service connection is automatically available to pipelines that reference it:

```yaml
resources:
  repositories:
    - repository: tooling
      type: github
      name: raboley/tooling
      endpoint: raboley  # This matches the service connection name
      ref: refs/heads/main
```

## Troubleshooting

### Missing GitHub Token

If you see errors during `task ado-up` about missing `GITHUB_TOKEN`:

1. Ensure your `.env` file contains `GITHUB_TOKEN=your_token_here`
2. Verify the token has the correct scopes (at minimum `public_repo`)
3. Run `task ado-up` again

### Pipeline Preview Still Failing

If pipeline preview tests still fail with 400 errors after Terraform deployment:

1. Check that the service connection was created:
   ```bash
   # View the Terraform state
   cd terraform && terraform show | grep github_connection
   ```

2. Verify in Azure DevOps UI:
   - Go to Project Settings → Service connections
   - Look for a connection named "raboley"
   - Verify its status is "Ready"

3. Check GitHub token permissions:
   - Token must have access to the `raboley/tooling` repository
   - For private repos, `repo` scope is required

### Service Connection Authentication Issues

If the service connection shows as "Not verified" or authentication fails:

1. **Token Expiration**: GitHub tokens expire - generate a new one
2. **Insufficient Permissions**: Ensure token has `repo` scope for private repositories
3. **Repository Access**: Token owner must have access to `raboley/tooling` repository

## Manual Verification

After running `task ado-up`, you can verify the service connection:

1. **In Azure DevOps**:
   - Navigate to your project → Project Settings → Service connections
   - Look for "raboley" connection
   - Status should be "Ready" (green checkmark)

2. **Test Pipeline Preview**:
   ```bash
   task test-single TEST_NAME=tests/preview/test_preview_pipeline_github_resources.py::TestPreviewPipelineGitHubResources::test_preview_public_github_repository_default_behavior
   ```

## Environment Variables Summary

Required environment variables in `.env`:

```bash
# Azure DevOps
AZURE_DEVOPS_EXT_PAT=your_ado_token_here
AZDO_PERSONAL_ACCESS_TOKEN=your_ado_token_here  # Same token, different variable name
ADO_ORGANIZATION_URL=https://dev.azure.com/YourOrgName

# GitHub (NEW - required for service connection)
GITHUB_TOKEN=your_github_token_here

# Project configuration
ADO_PROJECT_NAME=ado-mcp2
```

## Security Notes

- Both tokens are marked as sensitive in Terraform
- Tokens are not stored in Terraform state in plain text
- Always use fine-grained personal access tokens when possible
- Regularly rotate tokens for security