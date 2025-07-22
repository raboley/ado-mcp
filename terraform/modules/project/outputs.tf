output "project_id" {
  description = "The ID of the created project"
  value       = azuredevops_project.test_project.id
}

output "project_name" {
  description = "The name of the created project"
  value       = azuredevops_project.test_project.name
}

output "project_url" {
  description = "The URL of the created project"  
  value       = "https://dev.azure.com/RussellBoley/${azuredevops_project.test_project.name}"
}

output "repository_id" {
  description = "The ID of the default repository"
  value       = azuredevops_git_repository.test_repo.id
}

output "repository_name" {
  description = "The name of the default repository"
  value       = azuredevops_git_repository.test_repo.name
}