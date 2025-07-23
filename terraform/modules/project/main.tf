resource "azuredevops_project" "test_project" {
  name               = var.project_name
  description        = var.project_description
  visibility         = "private"
  version_control    = "Git"
  work_item_template = "Agile"
  
  features = {
    "boards"       = "enabled"
    "repositories" = "enabled"
    "pipelines"    = "enabled"
    "testplans"    = "disabled"
    "artifacts"    = "enabled"
  }
}

# Create a default repository in the project
resource "azuredevops_git_repository" "test_repo" {
  project_id = azuredevops_project.test_project.id
  name       = "${var.project_name}-repo"
  
  initialization {
    init_type = "Clean"
  }
}