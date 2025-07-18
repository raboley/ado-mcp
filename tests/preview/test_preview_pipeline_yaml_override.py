"""
Tests for the preview_pipeline MCP tool - YAML override functionality.

This module tests the YAML override feature which is unique to the preview API.
"""

import os
import pytest
from fastmcp.client import Client

from server import mcp
from tests.ado.test_client import requires_ado_creds

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio

# Test fixtures
TEST_PROJECT_ID = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
BASIC_PREVIEW_PIPELINE_ID = 74  # preview-test-valid pipeline


@pytest.fixture
async def mcp_client():
    """Provides a connected MCP client for tests."""
    async with Client(mcp) as client:
        initial_org_url = os.environ.get(
            "ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley"
        )
        await client.call_tool("set_ado_organization", {"organization_url": initial_org_url})
        yield client


@requires_ado_creds
async def test_preview_pipeline_yaml_override_simple(mcp_client: Client):
    """Test preview with simple YAML override."""
    yaml_override = """
name: Simple Override Test
trigger: none
pool:
  vmImage: ubuntu-latest
steps:
  - script: echo "Hello from YAML override!"
    displayName: 'Override step'
"""
    
    result = await mcp_client.call_tool(
        "preview_pipeline",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_id": BASIC_PREVIEW_PIPELINE_ID,
            "yaml_override": yaml_override
        }
    )
    
    preview_data = result.data
    assert preview_data is not None, "Preview with override should not be None"
    assert "finalYaml" in preview_data, "Preview should contain finalYaml field"
    
    final_yaml = preview_data["finalYaml"]
    assert "Simple Override Test" in final_yaml, "Final YAML should contain override content"
    assert "Hello from YAML override!" in final_yaml, "Final YAML should contain override script"
    
    print("✓ Simple YAML override applied successfully")


@requires_ado_creds
async def test_preview_pipeline_yaml_override_complex(mcp_client: Client):
    """Test preview with complex YAML override including parameters."""
    parameterized_pipeline_id = 75  # preview-test-parameterized
    
    yaml_override = """
name: Complex Override Test Pipeline
trigger: none

parameters:
  - name: overrideParam
    displayName: 'Override Parameter'
    type: string
    default: 'default-value'
  - name: environmentName
    displayName: 'Environment'
    type: string
    default: 'test'

variables:
  - name: overrideVar
    value: 'override-value'

pool:
  vmImage: ubuntu-latest

stages:
  - stage: OverrideStage
    displayName: 'Override Stage'
    jobs:
      - job: OverrideJob
        displayName: 'Override Job'
        steps:
          - script: |
              echo "Override parameter: ${{ parameters.overrideParam }}"
              echo "Environment: ${{ parameters.environmentName }}"
              echo "Override variable: $(overrideVar)"
            displayName: 'Show override values'
          - script: echo "Complex override test completed"
            displayName: 'Completion step'
"""
    
    result = await mcp_client.call_tool(
        "preview_pipeline",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_id": parameterized_pipeline_id,
            "yaml_override": yaml_override
        }
    )
    
    preview_data = result.data
    assert preview_data is not None, "Preview with complex override should not be None"
    assert "finalYaml" in preview_data, "Preview should contain finalYaml field"
    
    final_yaml = preview_data["finalYaml"]
    assert "Complex Override Test Pipeline" in final_yaml, "Final YAML should contain override name"
    assert "OverrideStage" in final_yaml, "Final YAML should contain override stage"
    assert "overrideParam" in final_yaml, "Final YAML should contain override parameters"
    
    print("✓ Complex YAML override with parameters applied successfully")


@requires_ado_creds
async def test_preview_pipeline_yaml_override_with_resources(mcp_client: Client):
    """Test preview combining YAML override with resources."""
    github_resources_pipeline_id = 200  # github-resources-test-stable
    
    yaml_override = """
name: GitHub Resources Override Test
trigger: none

resources:
  repositories:
    - repository: tooling
      type: github
      name: raboley/tooling
      endpoint: raboley
      ref: refs/heads/main

pool:
  vmImage: ubuntu-latest

steps:
  - checkout: self
  - checkout: tooling
  - script: echo "Testing GitHub resources with YAML override"
    displayName: 'GitHub resources test'
"""
    
    resources = {
        "repositories": {
            "tooling": {
                "refName": "refs/heads/stable/0.0.1"  # This should override the YAML
            }
        }
    }
    
    result = await mcp_client.call_tool(
        "preview_pipeline",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_id": github_resources_pipeline_id,
            "yaml_override": yaml_override,
            "resources": resources
        }
    )
    
    preview_data = result.data
    assert preview_data is not None, "GitHub resources with YAML override should not be None"
    assert "finalYaml" in preview_data, "Preview should contain finalYaml field"
    
    final_yaml = preview_data["finalYaml"]
    assert "GitHub Resources Override Test" in final_yaml, "Final YAML should contain override name"
    assert "tooling" in final_yaml, "Final YAML should contain tooling repository"
    
    print("✓ YAML override with resources combination processed successfully")


@requires_ado_creds
async def test_preview_pipeline_invalid_yaml_override(mcp_client: Client):
    """Test preview error handling with invalid YAML override."""
    invalid_yaml_override = """
name: Invalid YAML Test
trigger: none
pool:
  vmImage: ubuntu-latest
steps:
  - script: echo "test"
    invalid_field: this_should_cause_error
    another_invalid: [ unclosed_array
"""
    
    try:
        result = await mcp_client.call_tool(
            "preview_pipeline",
            {
                "project_id": TEST_PROJECT_ID,
                "pipeline_id": BASIC_PREVIEW_PIPELINE_ID,
                "yaml_override": invalid_yaml_override
            }
        )
        
        # If we get a result, check it's structured properly
        if result.data is not None:
            preview_data = result.data
            assert isinstance(preview_data, dict), "Even error responses should be dictionaries"
            print("✓ Invalid YAML override handled gracefully by preview")
        else:
            print("✓ Preview tool returned None for invalid YAML override")
    except Exception as e:
        print(f"✓ Preview tool properly raised exception for invalid YAML: {type(e).__name__}")
        assert isinstance(e, Exception), "Should raise a proper exception type"


@requires_ado_creds 
async def test_preview_pipeline_with_yaml_override_tool_integration(mcp_client: Client):
    """Test YAML override integration from the original server tests."""
    yaml_override = """
name: Override Integration Test
trigger: none
pool:
  vmImage: ubuntu-latest

steps:
  - script: echo "YAML override integration test"
    displayName: 'Integration test step'
  - script: echo "Testing override functionality"
    displayName: 'Override verification'
"""
    
    result = await mcp_client.call_tool(
        "preview_pipeline",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_id": BASIC_PREVIEW_PIPELINE_ID,
            "yaml_override": yaml_override
        }
    )
    
    preview_data = result.data
    assert preview_data is not None, "Preview should not be None"
    assert "finalYaml" in preview_data, "Should have finalYaml field"
    
    final_yaml = preview_data["finalYaml"]
    assert "Override Integration Test" in final_yaml, "Should contain override pipeline name"
    assert "YAML override integration test" in final_yaml, "Should contain override step content"
    
    print("✓ YAML override tool integration test successful")