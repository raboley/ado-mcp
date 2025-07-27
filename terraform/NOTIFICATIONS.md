# Azure DevOps Notification Management

## Current Limitation

The Azure DevOps Terraform provider **does not support managing notification settings**. This is a known limitation tracked in [issue #907](https://github.com/microsoft/terraform-provider-azuredevops/issues/907).

## Automatic Integration

The `ado-up` task now **automatically disables pipeline email notifications** after provisioning the infrastructure. This runs automatically and requires no additional configuration.

## Manual Options

### Option 1: Task Command (Recommended)

Run the dedicated task to disable notifications:

```bash
task disable-notifications
```

This automatically uses the correct organization and project from your environment.

### Option 2: Shell Script (Cross-platform)

Use the shell script directly:

```bash
# Uses defaults from environment
./scripts/disable-notifications.sh

# Or specify organization and project
./scripts/disable-notifications.sh "YourOrg" "YourProject"
```

### Option 3: PowerShell Script (Windows/PowerShell Core)

```powershell
# Set your PAT token
$env:AZURE_DEVOPS_EXT_PAT = "your-pat-token"

# Run the script
./scripts/disable-notifications.ps1 -Organization "your-org" -ProjectName "your-project"
```

### Option 4: Manual Configuration

1. Go to your Azure DevOps organization: `https://dev.azure.com/{organization}`
2. Click your profile picture → **Notification settings**
3. Find these notification types and toggle them **Off**:
   - Build completes
   - Build fails
   - Pipeline completion
   - Release deployment started/completed/failed

For organization-wide settings:
1. Go to **Project Settings** → **Notifications**
2. Disable pipeline-related notifications for all users

### Option 3: REST API Direct Calls

You can also make direct REST API calls to manage notification subscriptions:

```bash
# List all notification subscriptions
curl -u ":$AZURE_DEVOPS_EXT_PAT" \
  "https://dev.azure.com/{organization}/_apis/notification/subscriptions?api-version=7.1-preview.1"

# Disable a specific subscription
curl -u ":$AZURE_DEVOPS_EXT_PAT" \
  -X PATCH \
  -H "Content-Type: application/json" \
  -d '{"status": "disabled"}' \
  "https://dev.azure.com/{organization}/_apis/notification/subscriptions/{subscriptionId}?api-version=7.1-preview.1"
```

## Future Terraform Support

When notification support is added to the Terraform provider, the configuration might look like:

```hcl
resource "azuredevops_notification_subscription" "disable_pipeline_emails" {
  project_id = azuredevops_project.test_project.id
  
  notification_type = "build_completion"
  status           = "disabled"
  
  # or
  delivery_settings = {
    email_enabled = false
  }
}
```

This is speculative and will depend on the actual implementation when it becomes available.