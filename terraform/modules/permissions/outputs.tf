output "service_connection_ids" {
  description = "Map of service connection names to IDs (placeholder)"
  value = {
    "github-service-connection" = "placeholder-id"
  }
}

output "service_connection_configs" {
  description = "Service connection configurations for testing"
  value = local.required_service_connections
}

output "permissions_requirements_file" {
  description = "Path to the permissions setup requirements file"
  value       = local_file.permissions_requirements.filename
}