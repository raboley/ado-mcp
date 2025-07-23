# Testing Setup Guide

This guide explains how to set up a testing environment for ado-mcp using the new Terraform-based infrastructure system.

## Overview

The ado-mcp project now uses a dynamic, Terraform-managed testing infrastructure that eliminates hardcoded values and enables easy setup across different Azure DevOps organizations.

## Quick Start

### Prerequisites

1. **Azure DevOps Organization**: You need an Azure DevOps organization where you have admin rights
2. **Personal Access Token (PAT)**: With the following permissions:
   - Project and team (read, write, & manage)
   - Build (read & execute)  
   - Code (read)
   - Work items (read & write)
3. **Terraform**: Installed on your machine (`task install-terraform` will install via Homebrew)

### Setup Steps

1. **Clone the repository** (if you haven't already):
   ```bash
   git clone <repository-url>
   cd ado-mcp
   ```

2. **Install dependencies**:
   ```bash
   task install
   ```

3. **Configure environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env file with your values:
   # - AZURE_DEVOPS_EXT_PAT: Your PAT token
   # - ADO_ORGANIZATION_URL: Your organization URL (e.g., https://dev.azure.com/YourOrg)
   ```

4. **Provision test environment**:
   ```bash
   task ado-up
   ```

5. **Set up pipelines** (automatically handled):
   - YAML files are automatically copied to the Azure DevOps repository
   - Pipelines are created via Terraform configuration
   - No manual pipeline creation required

6. **Run tests**:
   ```bash
   task test
   ```

7. **Tear down environment** (when done):
   ```bash
   task ado-down
   ```

## Detailed Configuration

### Environment Variables

The following environment variables are required:

```bash
# Your Azure DevOps Personal Access Token
AZURE_DEVOPS_EXT_PAT=your_token_here

# Your Azure DevOps organization URL  
ADO_ORGANIZATION_URL=https://dev.azure.com/YourOrganizationName

# Test project name (will be created by Terraform)
ADO_PROJECT_NAME=ado-mcp2
```

### Getting a Personal Access Token

1. Go to your Azure DevOps organization
2. Click on your profile picture → "Personal access tokens"
3. Create a new token with these permissions:
   - **Project and team**: Read, write, & manage
   - **Build**: Read & execute
   - **Code**: Read
   - **Work items**: Read & write
4. Copy the token and add it to your `.env` file

### Terraform Infrastructure

The Terraform configuration creates:

- **Project**: `ado-mcp2` (configurable via variable)
- **Repository**: Default Git repository in the project
- **Configuration files**: JSON files with resource mappings

## Test Pipeline Setup

Currently, pipelines must be created manually in Azure DevOps. Here are the required pipelines:

| Pipeline Name | YAML File | Description |
|---------------|-----------|-------------|
| `test_run_and_get_pipeline_run_details` | `tests/ado/fixtures/fast.test.pipeline.yml` | Fast test pipeline for basic operations |
| `slow.log-test-complex` | `tests/ado/fixtures/complex-pipeline.yml` | Complex pipeline for failure testing |
| `log-test-failing` | `tests/ado/fixtures/failing-pipeline.yml` | Pipeline designed to fail |
| `preview-test-parameterized` | `tests/ado/fixtures/parameterized-preview.yml` | Parameterized pipeline for preview tests |
| `preview-test-valid` | `tests/ado/fixtures/valid-preview.yml` | Basic preview pipeline |
| `github-resources-test-stable` | `tests/ado/fixtures/github-resources-test.yml` | Pipeline with GitHub resources |
| `runtime-variables-test` | `tests/ado/fixtures/runtime-variables-test.yml` | Runtime variables test pipeline |

### Pipeline Creation Steps

1. **Navigate to your Azure DevOps project**
2. **Go to Pipelines > Create Pipeline**
3. **Choose "Azure Repos Git"** and select your repository
4. **Choose "Existing Azure Pipelines YAML file"**
5. **Select the appropriate YAML file** from the `tests/ado/fixtures/` directory
6. **Save the pipeline** with the exact name specified in the table above

**Important**: Pipeline names must exactly match the table above for tests to work correctly.

## Dynamic Configuration System

The new test infrastructure uses a dynamic configuration system that:

- **Loads resource IDs** from `tests/terraform_config.json`
- **Provides helper functions** for getting project/pipeline IDs
- **Eliminates hardcoded values** from test files
- **Supports multiple environments** seamlessly

### Configuration File Structure

```json
{
  "project": {
    "id": "project-uuid-here",
    "name": "ado-mcp2", 
    "url": "https://dev.azure.com/YourOrg/ado-mcp2"
  },
  "pipelines": {
    "test_run_and_get_pipeline_run_details": {
      "id": 123,
      "name": "test_run_and_get_pipeline_run_details",
      "yaml_path": "tests/ado/fixtures/fast.test.pipeline.yml"
    }
  },
  "organization_url": "https://dev.azure.com/YourOrg"
}
```

### Helper Functions

Test files use these helper functions instead of hardcoded values:

```python
from src.test_config import (
    get_project_id,
    get_organization_url,
    get_basic_pipeline_id,
    get_complex_pipeline_id,
    get_failing_pipeline_id
)

# Usage in tests
project_id = get_project_id()
pipeline_id = get_basic_pipeline_id()
```

## Running Tests

### All Tests
```bash
task test
```

### Sequential Tests (for debugging)
```bash
task test-sequential
```

### Tests with Extended Timeout
The test suite includes a 300-second timeout per test to handle long-running operations:
```bash
# Default test run includes timeout
task test
```

### Single Test
```bash
task test-single TEST_NAME=tests/test_example.py::test_function_name
```

### Test with Coverage
```bash
task coverage
```

## Troubleshooting

### Common Issues

**1. "Configuration file not found"**
- Run `task ado-up` to provision the test environment
- Ensure Terraform completed successfully

**2. "Pipeline 'xxx' not found in configuration"**
- Verify all required pipelines are created in Azure DevOps
- Check that pipeline names exactly match the required names
- Update the configuration file if pipeline IDs have changed

**3. "Permission denied" errors**
- Verify your PAT token has the required permissions
- Check that the token hasn't expired
- Ensure you have admin rights in the Azure DevOps organization

**4. Terraform fails**
- Check your Azure DevOps organization URL is correct
- Verify your PAT token is valid and has sufficient permissions
- Review the Terraform error messages for specific issues

### Test Environment Validation

You can validate your test environment setup:

```python
from src.test_config import validate_test_environment

validation = validate_test_environment()
print(validation)
```

This will show:
- Whether configuration is loaded correctly
- Which pipelines are properly configured
- Any missing or incorrectly configured resources

### Resetting the Environment

If you need to start fresh:

```bash
# Tear down current environment
task ado-down

# Remove configuration files
rm tests/terraform_config.json
rm terraform/terraform.tfstate*

# Provision fresh environment
task ado-up
```

## Advanced Configuration

### Using a Different Organization

1. Update `ADO_ORGANIZATION_URL` in your `.env` file
2. Update `TF_VAR_azure_devops_organization_url` if using Terraform directly
3. Run `task ado-down` then `task ado-up` to recreate resources

### Custom Project Names

1. Update the `project_name` variable in `terraform/variables.tf`
2. Or set `TF_VAR_project_name` environment variable
3. Run `task ado-up` to apply changes

### Running in CI/CD

For automated environments:

1. **Set environment variables** in your CI/CD system
2. **Use service principals** instead of personal access tokens
3. **Consider shared test environments** vs. isolated per-run environments
4. **Implement cleanup** to avoid resource accumulation

Example CI/CD setup:
```yaml
env:
  AZURE_DEVOPS_EXT_PAT: ${{ secrets.ADO_PAT }}
  ADO_ORGANIZATION_URL: ${{ vars.ADO_ORG_URL }}

steps:
  - run: task ado-up
  - run: task test
  - run: task ado-down
    if: always()
```

## Migration Notes

### For Existing Contributors

If you're upgrading from the old hardcoded system:

1. **Pull latest changes** from the repository
2. **Remove any hardcoded project/pipeline IDs** from your local customizations
3. **Set up the new environment** using this guide
4. **Verify tests pass** with your setup

### Breaking Changes

- **Hardcoded project/pipeline IDs** no longer work
- **Tests now require** the Terraform configuration to be present
- **Environment variables** are now required for testing

The new system is more robust but requires initial setup. Once configured, it's much easier to maintain and work with across different environments.

## Support

If you encounter issues:

1. **Check this documentation** for solutions
2. **Review the troubleshooting section** above  
3. **Validate your environment** using the validation tools
4. **Check the issue tracker** for known problems
5. **Create an issue** with detailed error information if needed