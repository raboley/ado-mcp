# Tasks: Terraform-Based Test Infrastructure

## Relevant Files

- `terraform/main.tf` - Main Terraform configuration for Azure DevOps resources
- `terraform/variables.tf` - Terraform variable definitions including organization URL
- `terraform/outputs.tf` - Terraform outputs for resource identifiers and names
- `terraform/modules/project/main.tf` - Module for creating Azure DevOps projects
- `terraform/modules/pipeline/main.tf` - Module for creating pipelines with matching YAML names
- `terraform/modules/permissions/main.tf` - Module for setting up permissions and service connections
- `src/test_config.py` - Dynamic test configuration loader using resource names
- `src/test_config.py` - Test configuration validation and error handling
- `tests/test_test_config.py` - End-to-end tests for configuration system
- `Taskfile.yml` - Updated with `ado-up` and `ado-down` commands
- `.env.example` - Template showing required environment variables
- `tests/integration/test_projects.py` - Refactored project tests using names
- `tests/integration/test_pipelines.py` - Refactored pipeline tests using names  
- `tests/integration/test_workitems.py` - Refactored work item tests using names
- `tests/e2e/` - All end-to-end test files requiring refactoring
- `docs/TESTING_SETUP.md` - Comprehensive testing setup documentation
- `docs/TERRAFORM_TROUBLESHOOTING.md` - Troubleshooting guide for common issues

### Notes

- Use `task test` for running all tests after refactoring
- Each parent task represents a complete vertical slice (code + tests + observability + docs)
- Terraform will use local state file for simplicity
- Pipeline names will exactly match YAML file names to eliminate mapping

## Tasks

- [ ] 1.0 Terraform Foundation and Environment Management (Complete Vertical Slice)
  - [ ] 1.1 Create Terraform directory structure with main configuration files
  - [ ] 1.2 Implement Azure DevOps provider configuration using .env variables
  - [ ] 1.3 Create project module that provisions test projects with standardized names
  - [ ] 1.4 Create pipeline module that reads YAML files and creates matching pipeline names
  - [ ] 1.5 Create permissions module for service connections and access rights
  - [ ] 1.6 Add Terraform outputs for all provisioned resource names and IDs
  - [ ] 1.7 Update Taskfile.yml with `ado-up` and `ado-down` commands
  - [ ] 1.8 Add environment variable validation in Taskfile commands
  - [ ] 1.9 Create .env.example with required ADO_ORGANIZATION_URL variable
  - [ ] 1.10 Test Terraform provisioning end-to-end with real Azure DevOps organization
  - [ ] 1.11 Test Terraform teardown functionality and state cleanup
  - [ ] 1.12 Add logging and error handling for Terraform operations
  - [ ] 1.13 Create initial documentation for environment setup process

- [ ] 2.0 Dynamic Test Configuration System (Complete Vertical Slice)
  - [ ] 2.1 Create test_config.py module for loading Terraform outputs
  - [ ] 2.2 Implement name-based resource lookup functions (projects, pipelines, etc.)
  - [ ] 2.3 Add fallback mechanisms for when resources don't exist
  - [ ] 2.4 Implement configuration validation with clear error messages
  - [ ] 2.5 Add caching for repeated resource lookups during test runs
  - [ ] 2.6 Create comprehensive error handling with troubleshooting guidance
  - [ ] 2.7 Add logging for all configuration operations and lookups
  - [ ] 2.8 Write end-to-end tests for configuration system using real resources
  - [ ] 2.9 Test configuration system with missing resources (error cases)
  - [ ] 2.10 Create utility functions for common test resource patterns
  - [ ] 2.11 Document configuration system API and usage patterns

- [ ] 3.0 Project Tests Migration (Complete Vertical Slice)
  - [ ] 3.1 Audit tests/integration/test_projects.py for hardcoded values
  - [ ] 3.2 Replace hardcoded project IDs with name-based lookups
  - [ ] 3.3 Update project creation tests to use standardized naming
  - [ ] 3.4 Add validation that test projects exist before running tests
  - [ ] 3.5 Update project-related assertions to use dynamic values
  - [ ] 3.6 Add logging for all project test operations
  - [ ] 3.7 Run project tests against Terraform-provisioned environment
  - [ ] 3.8 Create documentation for project test patterns and conventions
  - [ ] 3.9 Verify all project tests pass with new configuration system

- [ ] 4.0 Pipeline Tests Migration (Complete Vertical Slice)
  - [ ] 4.1 Audit tests/integration/test_pipelines.py for hardcoded values
  - [ ] 4.2 Replace hardcoded pipeline IDs with name-based lookups
  - [ ] 4.3 Ensure pipeline YAML files match expected pipeline names exactly
  - [ ] 4.4 Update pipeline run tests to use dynamic pipeline resolution
  - [ ] 4.5 Refactor pipeline failure analysis tests for name-based lookup
  - [ ] 4.6 Update pipeline creation/deletion tests for standardized naming
  - [ ] 4.7 Add validation that test pipelines exist before running tests
  - [ ] 4.8 Add logging for all pipeline test operations and lookups
  - [ ] 4.9 Run pipeline tests against Terraform-provisioned environment
  - [ ] 4.10 Create documentation for pipeline test patterns and naming conventions
  - [ ] 4.11 Verify all pipeline tests pass with new configuration system

- [ ] 5.0 Work Items and E2E Tests Migration (Complete Vertical Slice)
  - [ ] 5.1 Audit tests/integration/test_workitems.py for hardcoded values
  - [ ] 5.2 Replace hardcoded work item project references with name lookups
  - [ ] 5.3 Update work item creation tests to use dynamic project resolution
  - [ ] 5.4 Refactor work item query tests for standardized project names
  - [ ] 5.5 Audit all tests/e2e/ files for hardcoded values by category
  - [ ] 5.6 Replace hardcoded values in e2e tests with dynamic configuration
  - [ ] 5.7 Update test data generation to use standardized naming patterns
  - [ ] 5.8 Add comprehensive validation for all test resource dependencies
  - [ ] 5.9 Add logging for work item and e2e test operations
  - [ ] 5.10 Run full test suite against Terraform-provisioned environment
  - [ ] 5.11 Create comprehensive testing documentation and troubleshooting guide
  - [ ] 5.12 Verify 100% test portability across different Azure DevOps organizations

- [ ] 6.0 Documentation and Contributor Experience (Complete Vertical Slice)
  - [ ] 6.1 Create comprehensive TESTING_SETUP.md with step-by-step instructions
  - [ ] 6.2 Document prerequisites (Azure DevOps org, admin rights, Terraform)
  - [ ] 6.3 Create TERRAFORM_TROUBLESHOOTING.md for common setup issues
  - [ ] 6.4 Add examples for setting up .env file with organization URL
  - [ ] 6.5 Document the complete contributor workflow from clone to test
  - [ ] 6.6 Create validation scripts for checking prerequisites
  - [ ] 6.7 Add clear error messages and remediation steps throughout system
  - [ ] 6.8 Test documentation with fresh Azure DevOps organization
  - [ ] 6.9 Create video or detailed walkthrough for new contributors
  - [ ] 6.10 Update main README.md with new testing setup instructions
  - [ ] 6.11 Add CI/CD integration documentation for automated environments
  - [ ] 6.12 Verify documentation enables 15-minute setup for new contributors