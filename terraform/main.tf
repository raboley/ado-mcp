terraform {
  required_providers {
    azuredevops = {
      source  = "microsoft/azuredevops"
      version = ">=0.10.0"
    }
  }
}

# Configure the Azure DevOps Provider
# Uses environment variables:
# - AZDO_ORG_SERVICE_URL
# - AZDO_PERSONAL_ACCESS_TOKEN
provider "azuredevops" {}

# Create the main test project
module "test_project" {
  source = "./modules/project"
  
  project_name        = var.project_name
  project_description = var.project_description
}

# Create test pipelines that match YAML file names
module "test_pipelines" {
  source = "./modules/pipeline"
  
  project_id    = module.test_project.project_id
  repository_id = module.test_project.repository_id
  
  depends_on = [module.test_project]
}

# Set up permissions and service connections
module "permissions" {
  source = "./modules/permissions"
  
  project_id    = module.test_project.project_id
  github_token  = var.github_token
  
  depends_on = [module.test_project]
}