# Project outputs
output "project_id" {
  description = "The ID of the created test project"
  value       = module.test_project.project_id
}

output "project_name" {
  description = "The name of the created test project" 
  value       = module.test_project.project_name
}

output "project_url" {
  description = "The URL of the created test project"
  value       = module.test_project.project_url
}

# Pipeline outputs
output "pipeline_ids" {
  description = "Map of pipeline names to IDs"
  value       = module.test_pipelines.pipeline_ids
}

output "pipeline_names" {
  description = "List of created pipeline names"
  value       = module.test_pipelines.pipeline_names
}

# Service connection outputs
output "service_connection_ids" {
  description = "Map of service connection names to IDs"
  value       = module.permissions.service_connection_ids
}

# Generate test configuration file
resource "local_file" "test_config" {
  content = jsonencode({
    project = {
      id   = module.test_project.project_id
      name = module.test_project.project_name
      url  = module.test_project.project_url
    }
    pipelines = module.test_pipelines.pipeline_configs
    service_connections = module.permissions.service_connection_configs
    organization_url = "https://dev.azure.com/RussellBoley"
  })
  filename = "${path.root}/../tests/terraform_config.json"
}