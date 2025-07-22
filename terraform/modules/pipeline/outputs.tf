output "pipeline_ids" {
  description = "Map of pipeline names to their actual IDs"
  value = {
    for name, pipeline in azuredevops_build_definition.test_pipelines :
    name => tonumber(pipeline.id)
  }
}

output "pipeline_names" {
  description = "List of created pipeline names"
  value       = keys(azuredevops_build_definition.test_pipelines)
}

output "pipeline_configs" {
  description = "Complete pipeline configuration for testing"
  value = {
    for name, pipeline in azuredevops_build_definition.test_pipelines :
    name => {
      id = tonumber(pipeline.id)
      name = pipeline.name
      yaml_path = local.pipeline_definitions[name].yaml_path
      description = local.pipeline_definitions[name].description
    }
  }
}