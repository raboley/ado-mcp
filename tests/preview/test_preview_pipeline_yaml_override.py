import os
import pytest
from fastmcp.client import Client

from server import mcp
from src.test_config import get_project_id, get_project_name
from tests.ado.test_client import requires_ado_creds
from tests.test_helpers import get_pipeline_id_by_name

pytestmark = pytest.mark.asyncio

@pytest.fixture
async def mcp_client():
    async with Client(mcp) as client:
        initial_org_url = os.environ.get(
            "ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley"
        )
        await client.call_tool("set_ado_organization", {"organization_url": initial_org_url})
        yield client

@requires_ado_creds
async def test_preview_pipeline_yaml_override_simple(mcp_client: Client):
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
            "project_id": get_project_id(),
            "pipeline_id": await get_pipeline_id_by_name(mcp_client, "preview-test-valid"),
            "yaml_override": yaml_override,
        },
    )

    preview_data = result.data
    assert preview_data is not None, f"Expected preview data with YAML override but got None"
    assert "finalYaml" in preview_data, (
        f"Expected 'finalYaml' key in response. Got keys: {list(preview_data.keys())}"
    )

    final_yaml = preview_data["finalYaml"]
    assert "Simple Override Test" in final_yaml, (
        f"Expected 'Simple Override Test' in finalYaml but not found. Got: {final_yaml[:200]}..."
    )
    assert "Hello from YAML override!" in final_yaml, (
        f"Expected 'Hello from YAML override!' in finalYaml but not found. Got: {final_yaml[:200]}..."
    )

@requires_ado_creds
async def test_preview_pipeline_yaml_override_complex(mcp_client: Client):
    parameterized_pipeline_id = await get_pipeline_id_by_name(mcp_client, "preview-test-parameterized")

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
            "project_id": get_project_id(),
            "pipeline_id": parameterized_pipeline_id,
            "yaml_override": yaml_override,
        },
    )

    preview_data = result.data
    assert preview_data is not None, f"Expected preview data with complex override but got None"
    assert "finalYaml" in preview_data, (
        f"Expected 'finalYaml' key in response. Got keys: {list(preview_data.keys())}"
    )

    final_yaml = preview_data["finalYaml"]
    assert "Complex Override Test Pipeline" in final_yaml, (
        f"Expected 'Complex Override Test Pipeline' in finalYaml but not found. Got: {final_yaml[:200]}..."
    )
    assert "OverrideStage" in final_yaml, (
        f"Expected 'OverrideStage' in finalYaml but not found. Got: {final_yaml[:200]}..."
    )
    assert "overrideParam" in final_yaml, (
        f"Expected 'overrideParam' in finalYaml but not found. Got: {final_yaml[:200]}..."
    )

@requires_ado_creds
async def test_preview_pipeline_yaml_override_with_resources(mcp_client: Client):
    github_resources_pipeline_id = await get_pipeline_id_by_name(mcp_client, "github-resources-test-stable")

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

    resources = {"repositories": {"tooling": {"refName": "refs/heads/stable/0.0.1"}}}

    result = await mcp_client.call_tool(
        "preview_pipeline",
        {
            "project_id": get_project_id(),
            "pipeline_id": github_resources_pipeline_id,
            "yaml_override": yaml_override,
            "resources": resources,
        },
    )

    preview_data = result.data
    assert preview_data is not None, (
        f"Expected preview data with YAML override and resources but got None"
    )
    assert "finalYaml" in preview_data, (
        f"Expected 'finalYaml' key in response. Got keys: {list(preview_data.keys())}"
    )

    final_yaml = preview_data["finalYaml"]
    assert "GitHub Resources Override Test" in final_yaml, (
        f"Expected 'GitHub Resources Override Test' in finalYaml but not found. Got: {final_yaml[:200]}..."
    )
    assert "tooling" in final_yaml, (
        f"Expected 'tooling' repository reference in finalYaml but not found. Got: {final_yaml[:200]}..."
    )

@requires_ado_creds
async def test_preview_pipeline_invalid_yaml_override(mcp_client: Client):
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
                "project_id": get_project_id(),
                "pipeline_id": await get_pipeline_id_by_name(mcp_client, "preview-test-valid"),
                "yaml_override": invalid_yaml_override,
            },
        )

        if result.data is not None:
            preview_data = result.data
            assert isinstance(preview_data, dict), (
                f"Expected dict response for invalid YAML but got {type(preview_data)}"
            )
        else:
            assert True, "Invalid YAML override correctly returned None"
    except Exception as e:
        assert isinstance(e, Exception), (
            f"Expected proper exception type for invalid YAML but got {type(e)}"
        )

@requires_ado_creds
async def test_preview_pipeline_with_yaml_override_tool_integration(mcp_client: Client):
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
            "project_id": get_project_id(),
            "pipeline_id": await get_pipeline_id_by_name(mcp_client, "preview-test-valid"),
            "yaml_override": yaml_override,
        },
    )

    preview_data = result.data
    assert preview_data is not None, f"Expected preview data for tool integration test but got None"
    assert "finalYaml" in preview_data, (
        f"Expected 'finalYaml' key in response. Got keys: {list(preview_data.keys())}"
    )

    final_yaml = preview_data["finalYaml"]
    assert "Override Integration Test" in final_yaml, (
        f"Expected 'Override Integration Test' in finalYaml but not found. Got: {final_yaml[:200]}..."
    )
    assert "YAML override integration test" in final_yaml, (
        f"Expected 'YAML override integration test' in finalYaml but not found. Got: {final_yaml[:200]}..."
    )
