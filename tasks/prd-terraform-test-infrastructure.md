# PRD: Terraform-Based Test Infrastructure

## Introduction

This feature will replace the current hardcoded test infrastructure with a Terraform-managed, portable system that allows any contributor to set up and tear down a complete testing environment in their own Azure DevOps organization. The current system prevents contributions because tests are tightly coupled to specific hardcoded project IDs, pipeline IDs, and organization-specific resources.

The solution will enable contributors to clone the repository, set their organization variable, run Terraform to provision resources, and immediately run all tests successfully without manual configuration.

## Goals

- Enable any contributor with an Azure DevOps organization to run tests locally
- Eliminate all hardcoded test values (project IDs, pipeline IDs, resource names)
- Provide automated infrastructure provisioning and teardown
- Reduce contributor onboarding time from hours/days to minutes
- Ensure test consistency across different environments
- Make the codebase more maintainable by decoupling tests from specific implementations

## User Stories

**As a new open source contributor**, I want to run tests locally so that I can verify my changes work before submitting a pull request.

**As a new team member**, I want to set up a development environment quickly so that I can start contributing without lengthy manual setup processes.

**As a maintainer**, I want tests to be portable across environments so that I don't have to maintain environment-specific test configurations.

**As a CI/CD system**, I want to provision fresh test environments so that tests run in isolation without interference from previous runs.

**As a developer making changes**, I want to test against real Azure DevOps resources so that I can catch integration issues early.

## Functional Requirements

### Terraform Infrastructure Management
1. The system must provide Terraform configuration files that provision a complete Azure DevOps test environment
2. The system must accept an Azure DevOps organization URL as a variable input
3. The system must create Azure DevOps projects with standardized names for testing
4. The system must create pipelines with names that exactly match their YAML file names
5. The system must set up all necessary permissions and service connections for test execution
6. The system must generate a configuration file containing all provisioned resource identifiers
7. The system must support complete environment teardown through Terraform destroy

### Test Configuration System
8. The system must replace all hardcoded test values with dynamic lookups from a configuration file
9. The system must support both Terraform-generated outputs and manual configuration files
10. The system must use resource names instead of IDs for test lookups where possible
11. The system must provide fallback mechanisms when name-based lookups fail
12. The system must validate that all required test resources exist before running tests
13. The system must support separate configuration files per test category (projects, pipelines, work items, etc.)

### Pipeline and Resource Naming
14. The system must enforce that pipeline YAML file names match their Azure DevOps pipeline names
15. The system must use standardized naming conventions for all test resources
16. The system must support flexible mapping between file names and pipeline names through configuration
17. The system must provide clear error messages when naming conventions are violated

### User Experience
18. The system must provide a single command to provision the entire test environment
19. The system must include comprehensive setup documentation for new contributors
20. The system must validate user prerequisites (Azure DevOps admin rights, Terraform installation)
21. The system must provide clear error messages with remediation steps for common setup issues
22. The system must support both local development and CI/CD execution environments

## Non-Goals

- Supporting Azure DevOps Server (only Azure DevOps Services)
- Managing Azure resources outside of Azure DevOps (compute, storage, etc.)
- Providing GUI-based setup tools
- Supporting multiple organizations simultaneously in a single environment
- Migrating existing hardcoded tests gradually (will be a complete replacement)

## Design Considerations

### Configuration File Structure
- Use JSON or YAML format for easy parsing and human readability
- Organize by resource type (projects, pipelines, service-connections, etc.)
- Include both names and IDs for maximum compatibility
- Support environment-specific overrides

### Terraform Organization
- Separate modules for different Azure DevOps resource types
- Use consistent variable naming across modules
- Output all necessary identifiers for test configuration
- Include resource tagging for easy identification and cleanup

### Error Handling
- Provide specific error messages for missing permissions
- Include troubleshooting guides for common Terraform failures
- Validate configuration completeness before test execution
- Support partial environment recovery when possible

## Technical Considerations

### Dependencies
- Terraform Azure DevOps provider
- Azure CLI for authentication
- Azure DevOps PAT with appropriate permissions
- Python environment with updated test dependencies

### Integration Requirements
- Must work with existing pytest test suite
- Must integrate with current CI/CD pipeline
- Must support parallel test execution
- Must maintain backward compatibility during transition period

### Performance Considerations
- Terraform provisioning should complete within 5 minutes
- Test configuration loading should add minimal overhead
- Resource cleanup should be reliable and complete
- Support for incremental updates to avoid full reprovisioning

## Success Metrics

### Quantitative Measures
- Reduce contributor setup time from 2+ hours to under 15 minutes
- Achieve 100% test portability (all tests pass in any valid Azure DevOps org)
- Eliminate all hardcoded values from test files (0 remaining)
- Reduce test environment setup failures by 90%

### Qualitative Measures
- New contributors can successfully run tests on first attempt
- Maintainers report easier test debugging and maintenance
- CI/CD pipeline reliability improves with isolated test environments
- Documentation is clear enough for junior developers to follow

## Open Questions

### Resource Cleanup
- Should we implement automatic cleanup of old test resources?
- How should we handle failed Terraform operations that leave partial state?
- What's the policy for resource retention during development?

### Permission Management
- What's the minimum permission level required for contributors?
- Should we provide scripts to validate user permissions before setup?
- How should we handle organizations with strict permission policies?

### CI/CD Integration
- Should CI systems use shared or isolated test environments?
- How should we handle concurrent test runs in CI/CD?
- What's the strategy for managing Terraform state in automated environments?

### Migration Strategy
- Should we maintain both old and new test systems during transition?
- What's the plan for updating existing test data and expectations?
- How should we handle breaking changes in the test infrastructure?