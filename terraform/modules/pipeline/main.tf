# Define the test pipelines based on existing YAML files
locals {
  pipeline_definitions = {
    "test_run_and_get_pipeline_run_details" = {
      yaml_path = "tests/ado/fixtures/fast.test.pipeline.yml"
      description = "Fast test pipeline for basic run operations"
    }
    "slow.log-test-complex" = {
      yaml_path = "tests/ado/fixtures/complex-pipeline.yml"
      description = "Complex pipeline for testing failure scenarios and log retrieval"
    }
    "log-test-failing" = {
      yaml_path = "tests/ado/fixtures/failing-pipeline.yml"
      description = "Pipeline designed to fail for testing failure analysis"
    }
    "preview-test-parameterized" = {
      yaml_path = "tests/ado/fixtures/parameterized-preview.yml"
      description = "Parameterized pipeline for testing preview functionality"
    }
    "preview-test-valid" = {
      yaml_path = "tests/ado/fixtures/valid-preview.yml"
      description = "Valid pipeline for basic preview testing"
    }
    "github-resources-test-stable" = {
      yaml_path = "tests/ado/fixtures/github-resources-test.yml"
      description = "Pipeline with GitHub resources for testing external dependencies"
    }
    "runtime-variables-test" = {
      yaml_path = "tests/ado/fixtures/runtime-variables-test.yml"
      description = "Pipeline for testing runtime variable substitution"
    }
  }
}

# Create actual Azure DevOps build definitions using for_each
resource "azuredevops_build_definition" "test_pipelines" {
  for_each   = local.pipeline_definitions
  project_id = var.project_id
  name       = each.key
  
  repository {
    repo_type   = "TfsGit"
    branch_name = "refs/heads/master"
    repo_id     = var.repository_id
    yml_path    = each.value.yaml_path
  }
  
  ci_trigger {
    use_yaml = true
  }
  
  # Optional: Set agent pool
  agent_pool_name = "Azure Pipelines"
}