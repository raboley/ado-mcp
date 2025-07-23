# Terraform Troubleshooting Guide

This guide helps resolve common issues when using Terraform to provision Azure DevOps test environments for ado-mcp.

## Common Issues and Solutions

### 1. Authentication Issues

#### Error: "401 Unauthorized" or "403 Forbidden"

**Symptoms:**
```
Error: failed to get organization details: 401 Unauthorized
```

**Solutions:**

1. **Check PAT token validity:**
   ```bash
   # Test your token manually
   task auth-test
   ```

2. **Verify token permissions:**
   - Project and team (read, write, & manage)
   - Build (read & execute)
   - Code (read)
   - Work items (read & write)

3. **Check token expiration:**
   - Go to Azure DevOps → Profile → Personal access tokens
   - Verify your token hasn't expired
   - Create a new token if needed

4. **Verify organization URL:**
   ```bash
   echo $ADO_ORGANIZATION_URL
   # Should be: https://dev.azure.com/YourOrgName
   ```

#### Error: "Personal Access Token is not valid"

**Solutions:**

1. **Regenerate your PAT token** with correct permissions
2. **Update the token** in your environment:
   ```bash
   # Update in .env file
   AZURE_DEVOPS_EXT_PAT=your_new_token_here
   
   # Or update in keychain (macOS)
   security add-generic-password -a ado-token -s "Azure DevOps Token" -w your_new_token_here
   ```

### 2. Terraform Provider Issues

#### Error: "Could not load plugin" or "Provider registry.terraform.io/microsoft/azuredevops"

**Symptoms:**
```
Error: Failed to install provider
Provider registry.terraform.io/microsoft/azuredevops could not be found
```

**Solutions:**

1. **Update Terraform to latest version:**
   ```bash
   brew upgrade terraform
   ```

2. **Clear Terraform cache:**
   ```bash
   cd terraform
   rm -rf .terraform/
   rm .terraform.lock.hcl
   terraform init
   ```

3. **Force provider download:**
   ```bash
   cd terraform
   terraform init -upgrade
   ```

### 3. Project Creation Issues

#### Error: "Project already exists"

**Symptoms:**
```
Error: project "ado-mcp2" already exists
```

**Solutions:**

1. **Use existing project** (recommended):
   - Import existing project into Terraform state:
   ```bash
   cd terraform
   terraform import azuredevops_project.test_project "existing-project-id"
   ```

2. **Use different project name:**
   ```bash
   # Edit terraform/variables.tf or set environment variable
   export TF_VAR_project_name="ado-mcp-test-$(whoami)"
   task ado-up
   ```

3. **Delete existing project** (careful - this removes all data):
   - Go to Azure DevOps project settings
   - Delete the project manually
   - Run `task ado-up` again

#### Error: "Insufficient permissions to create project"

**Solutions:**

1. **Check organization permissions:**
   - You need "Project Collection Administrators" or "Project Creation" rights
   - Contact your Azure DevOps admin if needed

2. **Use existing project** instead of creating new one:
   - Modify Terraform to reference existing project
   - Focus on creating pipelines in existing project

### 4. Pipeline Setup Issues

#### Error: "Repository not found"

**Symptoms:**
```
Error: repository "ado-mcp2-repo" not found
```

**Solutions:**

1. **Verify repository was created:**
   ```bash
   # Check Terraform output
   cd terraform
   terraform output
   ```

2. **Import existing repository:**
   ```bash
   cd terraform
   terraform import azuredevops_git_repository.test_repo "project-id/repo-id"
   ```

3. **Create repository manually** and update configuration

#### Pipeline Names Don't Match YAML Files

**Issue:** Pipeline created with wrong name, causing tests to fail

**Solutions:**

1. **Rename pipelines in Azure DevOps:**
   - Go to Pipelines → Select pipeline → Settings → Rename
   - Use exact names from requirements file

2. **Check naming requirements:**
   ```bash
   # View required pipeline names
   cat terraform/pipeline_setup_requirements.json
   ```

3. **Update test configuration:**
   ```bash
   # Edit tests/terraform_config.json to match actual pipeline names
   ```

### 5. State File Issues

#### Error: "State lock could not be acquired"

**Symptoms:**
```
Error: Error acquiring the state lock
Lock Info:
  ID:        xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  Path:      terraform.tfstate
```

**Solutions:**

1. **Check if Terraform is running elsewhere:**
   ```bash
   ps aux | grep terraform
   ```

2. **Force unlock** (if you're sure no other Terraform is running):
   ```bash
   cd terraform
   terraform force-unlock LOCK_ID
   ```

3. **Remove state lock file** (local state only):
   ```bash
   cd terraform
   rm .terraform.tfstate.lock.info
   ```

#### Corrupted State File

**Solutions:**

1. **Backup current state:**
   ```bash
   cd terraform
   cp terraform.tfstate terraform.tfstate.backup
   ```

2. **Try to repair:**
   ```bash
   terraform refresh
   ```

3. **Start fresh** (last resort):
   ```bash
   cd terraform
   rm terraform.tfstate*
   # You'll need to manually clean up Azure DevOps resources
   terraform init
   task ado-up
   ```

### 6. Network and Connectivity Issues

#### Error: "Connection timeout" or "DNS resolution failed"

**Solutions:**

1. **Check internet connectivity:**
   ```bash
   ping dev.azure.com
   ```

2. **Check corporate proxy settings:**
   ```bash
   # If behind corporate proxy, set:
   export HTTPS_PROXY=http://proxy.company.com:8080
   export HTTP_PROXY=http://proxy.company.com:8080
   ```

3. **Verify Azure DevOps service status:**
   - Check https://status.dev.azure.com/

#### Error: "TLS handshake timeout"

**Solutions:**

1. **Update Terraform:**
   ```bash
   brew upgrade terraform
   ```

2. **Disable TLS verification** (temporary workaround):
   ```bash
   export TF_CLI_CONFIG_FILE=~/.terraformrc
   echo 'disable_checkpoint = true' > ~/.terraformrc
   ```

### 7. Resource Limits and Quotas

#### Error: "Quota exceeded" or "Too many requests"

**Solutions:**

1. **Wait and retry:**
   ```bash
   # Azure DevOps has rate limits
   sleep 60
   task ado-up
   ```

2. **Check organization limits:**
   - Go to Azure DevOps → Organization settings → Billing
   - Verify you haven't exceeded project/user limits

3. **Use existing resources** instead of creating new ones

### 8. Validation and Debugging

#### Enable Debug Logging

```bash
# Set Terraform debug level
export TF_LOG=DEBUG
export TF_LOG_PATH=./terraform-debug.log

# Run with verbose output
cd terraform
terraform plan -verbose
terraform apply -verbose
```

#### Validate Configuration

```bash
# Check Terraform syntax
cd terraform
terraform validate

# Check formatting
terraform fmt -check

# Plan without applying
terraform plan
```

#### Test Environment Validation

```bash
# Test with Python directly
python3 -c "
from src.test_config import validate_test_environment
import json
result = validate_test_environment()
print(json.dumps(result, indent=2))
"
```

## Prevention Tips

### Best Practices

1. **Always run `terraform plan`** before `terraform apply`
2. **Keep backups** of working terraform.tfstate files
3. **Use version control** for all Terraform files
4. **Test with minimal permissions** first
5. **Document any manual steps** required

### Environment Setup

1. **Use consistent naming** across environments
2. **Set up proper environment variables**:
   ```bash
   # In .env file
   AZURE_DEVOPS_EXT_PAT=your_token
   ADO_ORGANIZATION_URL=https://dev.azure.com/YourOrg
   TF_VAR_azure_devops_organization_url=https://dev.azure.com/YourOrg
   TF_VAR_azure_devops_personal_access_token=your_token
   ```

3. **Validate before committing** changes:
   ```bash
   task ado-up
   task test
   task ado-down
   ```

## Recovery Procedures

### Complete Environment Reset

If everything is broken:

1. **Clean up Azure DevOps resources manually:**
   - Delete test project from Azure DevOps UI
   - Remove any created service connections

2. **Reset Terraform state:**
   ```bash
   cd terraform
   rm -rf .terraform/
   rm terraform.tfstate*
   rm .terraform.lock.hcl
   ```

3. **Clean local configuration:**
   ```bash
   rm tests/terraform_config.json
   ```

4. **Start fresh:**
   ```bash
   task ado-up
   ```

### Partial Recovery

If only some resources are problematic:

1. **Identify problematic resources:**
   ```bash
   cd terraform
   terraform plan
   ```

2. **Remove from state** (doesn't delete actual resource):
   ```bash
   terraform state rm azuredevops_project.test_project
   ```

3. **Import existing resource:**
   ```bash
   terraform import azuredevops_project.test_project "project-id"
   ```

4. **Continue with apply:**
   ```bash
   terraform apply
   ```

## Getting Help

### Information to Gather

When seeking help, provide:

1. **Terraform version:**
   ```bash
   terraform version
   ```

2. **Azure DevOps provider version:**
   ```bash
   cd terraform
   terraform providers
   ```

3. **Environment details:**
   ```bash
   # Organization URL (sanitized)
   echo $ADO_ORGANIZATION_URL
   
   # OS and system info
   uname -a
   ```

4. **Error logs:**
   ```bash
   # Terraform logs
   TF_LOG=DEBUG terraform apply 2>&1 | tee terraform-error.log
   
   # Configuration validation
   python3 -c "from src.test_config import validate_test_environment; print(validate_test_environment())"
   ```

5. **Terraform state** (if safe to share):
   ```bash
   cd terraform
   terraform show
   ```

### Useful Commands for Debugging

```bash
# Check current state
cd terraform && terraform state list

# Show specific resource
terraform state show azuredevops_project.test_project

# Refresh state from actual resources
terraform refresh

# Import existing resource
terraform import azuredevops_project.test_project "project-id"

# Remove resource from state only
terraform state rm azuredevops_project.test_project

# Validate configuration
terraform validate

# Check what would change
terraform plan
```

Remember: When in doubt, it's often faster to tear down and recreate the test environment rather than trying to fix complex state issues.