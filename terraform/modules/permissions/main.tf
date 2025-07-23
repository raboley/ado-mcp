# Create GitHub service connection for testing repository resources
# This service connection is required for pipelines that use GitHub repositories

# Create GitHub service endpoint using personal access token
resource "azuredevops_serviceendpoint_github" "github_connection" {
  project_id                = var.project_id
  service_endpoint_name     = "raboley"  # Match the endpoint name used in pipeline YAML
  description               = "GitHub service connection for testing repository resources"
  
  auth_personal {
    personal_access_token = var.github_token
  }
}

locals {
  required_permissions = [
    "Build (read and execute)",
    "Pipeline (read, write, and execute)", 
    "Project (read)",
    "Work Items (read and write)",
    "Test Management (read and write)"
  ]
}

resource "local_file" "permissions_requirements" {
  content = jsonencode({
    service_connections = {
      "raboley" = {
        type = "GitHub"
        description = "GitHub service connection for testing repository resources"
        required_for = ["github-resources-test-stable pipeline"]
        id = azuredevops_serviceendpoint_github.github_connection.id
      }
    }
    permissions = local.required_permissions
    setup_instructions = [
      "Service connections created automatically via Terraform.",
      "Permissions Setup:",
      "- Ensure the user/service principal has required permissions",
      "- Test permissions by running basic operations"
    ]
  })
  filename = "${path.root}/permissions_setup_requirements.json"
}