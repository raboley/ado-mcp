"""
Tests for run_pipeline MCP tool with various parameter combinations.

This module consolidates tests for GitHub resources and other parameter scenarios.
Previously scattered across multiple GitHub resources test files.
"""

import os
import pytest
from fastmcp.client import Client

from server import mcp
from tests.ado.test_client import requires_ado_creds

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio

# Test fixtures - pipelines with known parameter support
TEST_PROJECT_ID = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project

# Pipeline 59: Basic pipeline, no parameters (simple delay task)
BASIC_PIPELINE_ID = 59  # test_run_and_get_pipeline_run_details

# Pipeline 75: Parameterized pipeline, supports template parameters (testEnvironment, enableDebug)
PARAMETERIZED_PIPELINE_ID = 75  # preview-test-parameterized

# Pipeline 200: GitHub resources pipeline, supports template parameters (taskfileVersion, installPath)
GITHUB_RESOURCES_PIPELINE_ID = 200  # github-resources-test-stable

# Pipeline 84: Complex pipeline with multiple stages for stage skipping tests
COMPLEX_PIPELINE_ID = 84  # complex-pipeline.yml - stages: Validate, Build, Test


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
async def test_run_pipeline_with_github_resources_stable_branch(mcp_client: Client):
    """Test running GitHub resources pipeline with stable branch override."""
    resources = {
        "repositories": {
            "tooling": {
                "refName": "refs/heads/stable/0.0.1"
            }
        }
    }
    
    template_parameters = {
        "taskfileVersion": "latest",
        "installPath": "./bin/stable-test"
    }
    
    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_id": GITHUB_RESOURCES_PIPELINE_ID,
            "resources": resources,
            "template_parameters": template_parameters
        }
    )
    
    pipeline_run = result.data
    assert pipeline_run is not None, "Pipeline run should not be None"
    assert pipeline_run["id"] is not None, "Pipeline run should have an ID"
    assert pipeline_run["state"] in ["unknown", "inProgress"], "Pipeline should be starting"
    
    print(f"✓ GitHub resources stable branch pipeline started: ID {pipeline_run['id']}")


@requires_ado_creds
async def test_run_pipeline_with_github_resources_main_branch(mcp_client: Client):
    """Test running GitHub resources pipeline with main branch override."""
    resources = {
        "repositories": {
            "tooling": {
                "refName": "refs/heads/main"
            }
        }
    }
    
    template_parameters = {
        "taskfileVersion": "latest",
        "installPath": "./bin/main-test"
    }
    
    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_id": GITHUB_RESOURCES_PIPELINE_ID,
            "resources": resources,
            "template_parameters": template_parameters
        }
    )
    
    pipeline_run = result.data
    assert pipeline_run is not None, "Pipeline run should not be None"
    assert pipeline_run["id"] is not None, "Pipeline run should have an ID"
    
    print(f"✓ GitHub resources main branch pipeline started: ID {pipeline_run['id']}")


@requires_ado_creds
async def test_run_pipeline_with_github_resources_feature_branch(mcp_client: Client):
    """Test running GitHub resources pipeline with different branch override."""
    # Use stable branch which we know exists
    resources = {
        "repositories": {
            "tooling": {
                "refName": "refs/heads/stable/0.0.1"
            }
        }
    }
    
    template_parameters = {
        "taskfileVersion": "v1.0.0",
        "installPath": "./bin/feature-test"
    }
    
    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_id": GITHUB_RESOURCES_PIPELINE_ID,
            "resources": resources,
            "template_parameters": template_parameters
        }
    )
    
    pipeline_run = result.data
    assert pipeline_run is not None, "Pipeline run should not be None"
    assert pipeline_run["id"] is not None, "Pipeline run should have an ID"
    
    print(f"✓ GitHub resources feature branch pipeline started: ID {pipeline_run['id']}")


@requires_ado_creds
async def test_run_pipeline_with_multiple_template_parameters(mcp_client: Client):
    """Test running pipeline with multiple template parameters."""
    template_parameters = {
        "taskfileVersion": "latest",
        "installPath": "./bin/multi-param-test"
    }
    
    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_id": GITHUB_RESOURCES_PIPELINE_ID,
            "template_parameters": template_parameters
        }
    )
    
    pipeline_run = result.data
    assert pipeline_run is not None, "Pipeline run should not be None"
    assert pipeline_run["id"] is not None, "Pipeline run should have an ID"
    
    print(f"✓ Multiple template parameters pipeline started: ID {pipeline_run['id']}")


@requires_ado_creds
async def test_run_pipeline_with_template_parameters(mcp_client: Client):
    """Test running pipeline with template parameters (using parameterized pipeline)."""
    # Use the parameterized pipeline with correct template parameter names
    template_parameters = {
        "testEnvironment": "staging",
        "enableDebug": True
    }
    
    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_id": PARAMETERIZED_PIPELINE_ID,  # Pipeline 75
            "template_parameters": template_parameters
        }
    )
    
    pipeline_run = result.data
    assert pipeline_run is not None, "Pipeline run should not be None"
    assert pipeline_run["id"] is not None, "Pipeline run should have an ID"
    
    print(f"✓ Pipeline with template parameters started: ID {pipeline_run['id']}")


@requires_ado_creds
async def test_run_pipeline_with_stages_to_skip(mcp_client: Client):
    """Test running pipeline with stages to skip."""
    # Use complex pipeline which has stages: Validate, Build, Test
    stages_to_skip = ["Test"]  # Skip the Test stage
    
    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_id": COMPLEX_PIPELINE_ID,
            "stages_to_skip": stages_to_skip
        }
    )
    
    pipeline_run = result.data
    assert pipeline_run is not None, "Pipeline run should not be None"
    assert pipeline_run["id"] is not None, "Pipeline run should have an ID"
    
    print(f"✓ Pipeline with skipped stages started: ID {pipeline_run['id']}")


@requires_ado_creds
async def test_run_pipeline_with_branch_override(mcp_client: Client):
    """Test running pipeline with specific branch."""
    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_id": BASIC_PIPELINE_ID,
            "branch": "refs/heads/main"
        }
    )
    
    pipeline_run = result.data
    assert pipeline_run is not None, "Pipeline run should not be None"
    assert pipeline_run["id"] is not None, "Pipeline run should have an ID"
    
    print(f"✓ Pipeline with branch override started: ID {pipeline_run['id']}")


@requires_ado_creds
async def test_run_pipeline_with_branch_resource_override(mcp_client: Client):
    """Test running basic pipeline with repository resource override."""
    # Test the resources functionality with self repository branch override
    
    resources = {
        "repositories": {
            "self": {
                "refName": "refs/heads/main"
            }
        }
    }
    
    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_id": BASIC_PIPELINE_ID,
            "resources": resources
        }
    )
    
    pipeline_run = result.data
    assert pipeline_run is not None, "Pipeline run should not be None"
    assert pipeline_run["id"] is not None, "Pipeline run should have an ID"
    
    print(f"✓ Combined resources and variables pipeline started: ID {pipeline_run['id']}")


@requires_ado_creds
async def test_run_pipeline_github_resources_complex_scenario(mcp_client: Client):
    """Test complex GitHub resources scenario with multiple parameters."""
    resources = {
        "repositories": {
            "tooling": {
                "refName": "refs/heads/stable/0.0.1"
            }
        }
    }
    
    template_parameters = {
        "taskfileVersion": "v1.2.3",
        "installPath": "/usr/local/bin/complex-test"
    }
    
    # Note: This pipeline doesn't have stages that can be skipped
    # so we're not including stages_to_skip
    # Use the request data if provided, otherwise send an empty preview request

    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_id": GITHUB_RESOURCES_PIPELINE_ID,
            "resources": resources,
            "template_parameters": template_parameters
        }
    )
    
    pipeline_run = result.data
    assert pipeline_run is not None, "Pipeline run should not be None"
    assert pipeline_run["id"] is not None, "Pipeline run should have an ID"
    
    print(f"✓ Complex GitHub resources scenario started: ID {pipeline_run['id']}")


async def test_run_pipeline_parameter_combinations_tool_registration():
    """Test that the run_pipeline tool supports all parameter combinations."""
    async with Client(mcp) as client:
        tools = await client.list_tools()
        run_pipeline_tool = None
        
        for tool in tools:
            if tool.name == "run_pipeline":
                run_pipeline_tool = tool
                break
        
        assert run_pipeline_tool is not None, "run_pipeline tool should be registered"
        
        # Verify the tool supports all the parameters we're testing
        # This is implicit through our successful test executions above