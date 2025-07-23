# Define the test pipelines based on existing YAML files
locals {
  pipeline_definitions = {
    "test_run_and_get_pipeline_run_details" = {
      yaml_path = "tests/ado/fixtures/fast.test.pipeline.yml"
      description = "Fast test pipeline for basic run operations"
      variables = {
        "testEnvironment" = {
          value = "dev"
          allow_override = true
        }
        "customVar" = {
          value = "default-value"
          allow_override = true
        }
      }
    }
    "slow.log-test-complex" = {
      yaml_path = "tests/ado/fixtures/complex-pipeline.yml"
      description = "Complex pipeline for testing failure scenarios and log retrieval"
      variables = {
        "buildConfiguration" = {
          value = "Release"
          allow_override = true
        }
        "appVersion" = {
          value = "1.0.0"
          allow_override = true
        }
        "customTestVar" = {
          value = "test-default"
          allow_override = true
        }
      }
    }
    "log-test-failing" = {
      yaml_path = "tests/ado/fixtures/failing-pipeline.yml"
      description = "Pipeline designed to fail for testing failure analysis"
      variables = {}
    }
    "preview-test-parameterized" = {
      yaml_path = "tests/ado/fixtures/parameterized-preview.yml"
      description = "Parameterized pipeline for testing preview functionality"
      variables = {}
    }
    "preview-test-valid" = {
      yaml_path = "tests/ado/fixtures/valid-preview.yml"
      description = "Valid pipeline for basic preview testing"
      variables = {}
    }
    "github-resources-test-stable" = {
      yaml_path = "tests/ado/fixtures/github-resources-test.yml"
      description = "Pipeline with GitHub resources for testing external dependencies"
      variables = {
        "environment" = {
          value = "staging"
          allow_override = true
        }
        "debugMode" = {
          value = "false"
          allow_override = true
        }
      }
    }
    "runtime-variables-test" = {
      yaml_path = "tests/ado/fixtures/runtime-variables-test.yml"
      description = "Pipeline for testing runtime variable substitution"
      variables = {
        "testVar" = {
          value = "default-test-value"
          allow_override = true
        }
        "environment" = {
          value = "test"
          allow_override = true
        }
      }
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
  
  # Configure queue-time settable variables
  dynamic "variable" {
    for_each = each.value.variables
    content {
      name           = variable.key
      value          = variable.value.value
      allow_override = variable.value.allow_override
    }
  }
  
  # Optional: Set agent pool
  agent_pool_name = "Azure Pipelines"
}