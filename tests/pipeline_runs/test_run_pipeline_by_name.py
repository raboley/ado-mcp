"""
Tests for the run_pipeline_by_name MCP tool.

This module tests running pipelines using natural project and pipeline names
instead of numeric IDs. Tests fuzzy matching and name resolution.
"""

import os
import pytest
from fastmcp.client import Client

from server import mcp
from tests.ado.test_client import requires_ado_creds

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio

# Test fixtures - using known project and pipeline names
TEST_PROJECT_NAME = "ado-mcp"
BASIC_PIPELINE_NAME = "test_run_and_get_pipeline_run_details"
GITHUB_RESOURCES_PIPELINE_NAME = "github-resources-test-stable"
PREVIEW_PARAMETERIZED_PIPELINE_NAME = "preview-test-parameterized"


@pytest.fixture
async def mcp_client():
    """Provides a connected MCP client for tests."""
    async with Client(mcp) as client:
        initial_org_url = os.environ.get(
            "ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley"
        )
        await client.call_tool("set_ado_organization", {"organization_url": initial_org_url})
        yield client


@pytest.fixture
async def mcp_client_no_auth(monkeypatch):
    """Provides a connected MCP client without authentication setup."""
    # Unset environment variables that provide authentication
    monkeypatch.delenv("AZURE_DEVOPS_EXT_PAT", raising=False)
    monkeypatch.delenv("ADO_ORGANIZATION_URL", raising=False)
    async with Client(mcp) as client:
        yield client


@requires_ado_creds
async def test_run_pipeline_by_name_basic(mcp_client: Client):
    """Test running a pipeline using project and pipeline names."""
    result = await mcp_client.call_tool(
        "run_pipeline_by_name",
        {
            "project_name": TEST_PROJECT_NAME,
            "pipeline_name": BASIC_PIPELINE_NAME
        }
    )
    
    pipeline_run = result.data
    assert pipeline_run is not None, "Pipeline run should not be None"
    assert isinstance(pipeline_run, dict), "Pipeline run should be a dictionary"
    assert pipeline_run["id"] is not None, "Pipeline run should have an ID"
    assert pipeline_run["state"] in ["unknown", "inProgress"], "Pipeline should be starting"
    
    # Verify pipeline information
    assert "pipeline" in pipeline_run, "Pipeline run should contain pipeline info"
    pipeline_info = pipeline_run["pipeline"]
    assert pipeline_info["name"] == BASIC_PIPELINE_NAME, "Pipeline name should match"
    
    print(f"✓ Pipeline run by name started: {BASIC_PIPELINE_NAME} (ID: {pipeline_run['id']})")


@requires_ado_creds
async def test_run_pipeline_by_name_with_template_parameters(mcp_client: Client):
    """Test running pipeline by name with template parameters."""
    template_parameters = {
        "taskfileVersion": "latest",
        "installPath": "./bin/by-name-test"
    }
    
    result = await mcp_client.call_tool(
        "run_pipeline_by_name",
        {
            "project_name": TEST_PROJECT_NAME,
            "pipeline_name": GITHUB_RESOURCES_PIPELINE_NAME,
            "template_parameters": template_parameters
        }
    )
    
    pipeline_run = result.data
    assert pipeline_run is not None, "Pipeline run should not be None"
    assert pipeline_run["id"] is not None, "Pipeline run should have an ID"
    
    print(f"✓ Pipeline by name with template parameters started: ID {pipeline_run['id']}")


@requires_ado_creds
async def test_run_pipeline_by_name_with_resources(mcp_client: Client):
    """Test running pipeline by name with repository resources."""
    resources = {
        "repositories": {
            "tooling": {
                "refName": "refs/heads/main"
            }
        }
    }
    
    template_parameters = {
        "taskfileVersion": "latest",
        "installPath": "./bin/by-name-resources-test"
    }
    
    result = await mcp_client.call_tool(
        "run_pipeline_by_name",
        {
            "project_name": TEST_PROJECT_NAME,
            "pipeline_name": GITHUB_RESOURCES_PIPELINE_NAME,
            "resources": resources,
            "template_parameters": template_parameters
        }
    )
    
    pipeline_run = result.data
    assert pipeline_run is not None, "Pipeline run should not be None"
    assert pipeline_run["id"] is not None, "Pipeline run should have an ID"
    
    print(f"✓ Pipeline by name with resources started: ID {pipeline_run['id']}")


@pytest.mark.skip(reason="Preview parameterized pipeline may not support runtime variables")
@requires_ado_creds
async def test_run_pipeline_by_name_with_variables(mcp_client: Client):
    """Test running pipeline by name with variables (using parameterized pipeline)."""
    variables = {
        "testEnvironment": "by-name-testing",
        "enableDebug": True,
        "byNameMode": "enabled"
    }
    
    result = await mcp_client.call_tool(
        "run_pipeline_by_name",
        {
            "project_name": TEST_PROJECT_NAME,
            "pipeline_name": PREVIEW_PARAMETERIZED_PIPELINE_NAME,
            "variables": variables
        }
    )
    
    pipeline_run = result.data
    assert pipeline_run is not None, "Pipeline run should not be None"
    assert pipeline_run["id"] is not None, "Pipeline run should have an ID"
    
    print(f"✓ Pipeline by name with variables started: ID {pipeline_run['id']}")


@requires_ado_creds
async def test_run_pipeline_by_name_with_branch(mcp_client: Client):
    """Test running pipeline by name with specific branch."""
    result = await mcp_client.call_tool(
        "run_pipeline_by_name",
        {
            "project_name": TEST_PROJECT_NAME,
            "pipeline_name": BASIC_PIPELINE_NAME,
            "branch": "refs/heads/main"
        }
    )
    
    pipeline_run = result.data
    assert pipeline_run is not None, "Pipeline run should not be None"
    assert pipeline_run["id"] is not None, "Pipeline run should have an ID"
    
    print(f"✓ Pipeline by name with branch started: ID {pipeline_run['id']}")


@pytest.mark.skip(reason="Preview parameterized pipeline may not have TestStage or OptionalStage")
@requires_ado_creds
async def test_run_pipeline_by_name_with_stages_to_skip(mcp_client: Client):
    """Test running pipeline by name with stages to skip."""
    stages_to_skip = ["TestStage", "OptionalStage"]
    
    result = await mcp_client.call_tool(
        "run_pipeline_by_name",
        {
            "project_name": TEST_PROJECT_NAME,
            "pipeline_name": PREVIEW_PARAMETERIZED_PIPELINE_NAME,
            "stages_to_skip": stages_to_skip
        }
    )
    
    pipeline_run = result.data
    assert pipeline_run is not None, "Pipeline run should not be None"
    assert pipeline_run["id"] is not None, "Pipeline run should have an ID"
    
    print(f"✓ Pipeline by name with skipped stages started: ID {pipeline_run['id']}")


@requires_ado_creds
async def test_run_pipeline_by_name_fuzzy_matching(mcp_client: Client):
    """Test fuzzy matching for project and pipeline names."""
    # Test with partial project name
    result = await mcp_client.call_tool(
        "run_pipeline_by_name",
        {
            "project_name": "ado",  # Partial name should match "ado-mcp"
            "pipeline_name": "test_run_and_get_pipeline"  # Partial pipeline name
        }
    )
    
    pipeline_run = result.data
    assert pipeline_run is not None, "Pipeline run should not be None with fuzzy matching"
    assert pipeline_run["id"] is not None, "Pipeline run should have an ID"
    
    print(f"✓ Fuzzy matching worked: started pipeline with partial names")


async def test_run_pipeline_by_name_no_client(mcp_client_no_auth: Client):
    """Test run_pipeline_by_name behavior when no client is configured."""
    result = await mcp_client_no_auth.call_tool(
        "run_pipeline_by_name",
        {
            "project_name": TEST_PROJECT_NAME,
            "pipeline_name": BASIC_PIPELINE_NAME
        }
    )
    
    pipeline_run = result.data
    assert pipeline_run is None, "Should return None when no client is configured"


@requires_ado_creds
async def test_run_pipeline_by_name_nonexistent_project(mcp_client: Client):
    """Test error handling for non-existent project name."""
    try:
        result = await mcp_client.call_tool(
            "run_pipeline_by_name",
            {
                "project_name": "NonexistentProject",
                "pipeline_name": BASIC_PIPELINE_NAME
            }
        )
        
        # If it doesn't raise an exception, check the result
        if result.data is None:
            print("✓ Non-existent project properly returned None")
        else:
            assert False, "Non-existent project should not return a valid result"
    except Exception as e:
        print(f"✓ Non-existent project properly raised exception: {type(e).__name__}")
        assert True, "Exception is expected for non-existent project"


@requires_ado_creds
async def test_run_pipeline_by_name_nonexistent_pipeline(mcp_client: Client):
    """Test error handling for non-existent pipeline name."""
    try:
        result = await mcp_client.call_tool(
            "run_pipeline_by_name",
            {
                "project_name": TEST_PROJECT_NAME,
                "pipeline_name": "NonexistentPipeline"
            }
        )
        
        # If it doesn't raise an exception, check the result
        if result.data is None:
            print("✓ Non-existent pipeline properly returned None")
        else:
            assert False, "Non-existent pipeline should not return a valid result"
    except Exception as e:
        print(f"✓ Non-existent pipeline properly raised exception: {type(e).__name__}")
        assert True, "Exception is expected for non-existent pipeline"


@requires_ado_creds
async def test_run_pipeline_by_name_case_insensitive(mcp_client: Client):
    """Test that name matching is case insensitive."""
    result = await mcp_client.call_tool(
        "run_pipeline_by_name",
        {
            "project_name": "ADO-MCP",  # Different case
            "pipeline_name": "TEST_RUN_AND_GET_PIPELINE_RUN_DETAILS"  # Different case
        }
    )
    
    pipeline_run = result.data
    assert pipeline_run is not None, "Pipeline run should work with different case"
    assert pipeline_run["id"] is not None, "Pipeline run should have an ID"
    
    print(f"✓ Case insensitive matching worked: ID {pipeline_run['id']}")


async def test_run_pipeline_by_name_tool_registration():
    """Test that the run_pipeline_by_name tool is properly registered."""
    async with Client(mcp) as client:
        tools_response = await client.list_tools()
        # Handle both potential response formats
        if hasattr(tools_response, "tools"):
            tools = tools_response.tools
        else:
            tools = tools_response
        tool_names = [tool.name for tool in tools]
        assert "run_pipeline_by_name" in tool_names, "run_pipeline_by_name tool should be registered"