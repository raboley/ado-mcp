output "service_connection_ids" {
  description = "Map of service connection names to IDs"
  value = {
    "raboley" = azuredevops_serviceendpoint_github.github_connection.id
  }
}

output "service_connection_configs" {
  description = "Service connection configurations for testing"
  value = {
    "raboley" = {
      type = "GitHub"
      description = "GitHub service connection for testing repository resources"
      required_for = ["github-resources-test-stable pipeline"]
      id = azuredevops_serviceendpoint_github.github_connection.id
    }
  }
}

output "permissions_requirements_file" {
  description = "Path to the permissions setup requirements file"
  value       = local_file.permissions_requirements.filename
}