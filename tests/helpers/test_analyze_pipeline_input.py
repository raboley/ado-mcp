"""
Tests for the analyze_pipeline_input MCP tool.

This module tests the input analysis helper for parsing Azure DevOps URLs and pipeline references.
"""

import os
import pytest
from fastmcp.client import Client

from server import mcp
from tests.ado.test_client import requires_ado_creds

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio


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
async def test_analyze_pipeline_input_with_build_url(mcp_client: Client):
    """Test analyzing Azure DevOps build results URL."""
    # Example build results URL with buildId
    test_url = "https://dev.azure.com/RussellBoley/ado-mcp/_build/results?buildId=12345&view=results"
    
    result = await mcp_client.call_tool(
        "analyze_pipeline_input",
        {"user_input": test_url}
    )
    
    analysis = result.data
    assert analysis is not None, "Analysis should not be None"
    assert isinstance(analysis, dict), "Analysis should be a dictionary"
    
    # Should extract organization and project from URL
    assert "organization" in analysis, "Should extract organization"
    assert "project" in analysis, "Should extract project"
    assert analysis["organization"] == "RussellBoley", "Should extract correct organization"
    assert analysis["project"] == "ado-mcp", "Should extract correct project"
    
    # Should identify build ID
    assert "build_id" in analysis or "run_id" in analysis, "Should extract build/run ID"
    
    print(f"✓ Successfully analyzed build URL: {analysis}")


@requires_ado_creds
async def test_analyze_pipeline_input_with_pipeline_definition_url(mcp_client: Client):
    """Test analyzing pipeline definition URL."""
    # Example pipeline definition URL
    test_url = "https://dev.azure.com/RussellBoley/ado-mcp/_build?definitionId=200"
    
    result = await mcp_client.call_tool(
        "analyze_pipeline_input",
        {"user_input": test_url}
    )
    
    analysis = result.data
    assert analysis is not None, "Analysis should not be None"
    assert isinstance(analysis, dict), "Analysis should be a dictionary"
    
    # Should identify pipeline definition ID
    assert "pipeline_id" in analysis or "definition_id" in analysis, "Should extract pipeline ID"
    
    print(f"✓ Successfully analyzed pipeline definition URL: {analysis}")


@requires_ado_creds
async def test_analyze_pipeline_input_with_pipeline_name(mcp_client: Client):
    """Test analyzing pipeline name input."""
    # Test with quoted pipeline name
    test_input = 'Run the "github-resources-test-stable" pipeline'
    
    result = await mcp_client.call_tool(
        "analyze_pipeline_input",
        {"user_input": test_input}
    )
    
    analysis = result.data
    assert analysis is not None, "Analysis should not be None"
    assert isinstance(analysis, dict), "Analysis should be a dictionary"
    
    # Should extract pipeline name
    assert "pipeline_name" in analysis, "Should extract pipeline name"
    assert "github-resources-test-stable" in str(analysis["pipeline_name"]), "Should extract correct pipeline name"
    
    print(f"✓ Successfully analyzed pipeline name: {analysis}")


@requires_ado_creds
async def test_analyze_pipeline_input_with_yaml_reference(mcp_client: Client):
    """Test analyzing YAML file reference."""
    test_input = "Deploy using azure-pipelines.yml from stable branch"
    
    result = await mcp_client.call_tool(
        "analyze_pipeline_input",
        {"user_input": test_input}
    )
    
    analysis = result.data
    assert analysis is not None, "Analysis should not be None"
    assert isinstance(analysis, dict), "Analysis should be a dictionary"
    
    # Should identify YAML file reference
    assert "yaml_path" in analysis or "azure-pipelines.yml" in str(analysis), "Should identify YAML reference"
    
    print(f"✓ Successfully analyzed YAML reference: {analysis}")


@requires_ado_creds
async def test_analyze_pipeline_input_with_mixed_input(mcp_client: Client):
    """Test analyzing complex mixed input."""
    test_input = 'Check why build 324 failed for "CI Pipeline" in project Learning'
    
    result = await mcp_client.call_tool(
        "analyze_pipeline_input",
        {
            "user_input": test_input,
            "project": "Learning"  # Provide additional context
        }
    )
    
    analysis = result.data
    assert analysis is not None, "Analysis should not be None"
    assert isinstance(analysis, dict), "Analysis should be a dictionary"
    
    # Should extract multiple pieces of information
    expected_fields = ["build_id", "pipeline_name", "project", "suggested_action"]
    found_fields = [field for field in expected_fields if field in analysis]
    
    assert len(found_fields) >= 2, f"Should extract multiple fields, found: {found_fields}"
    
    print(f"✓ Successfully analyzed mixed input: {analysis}")


@requires_ado_creds
async def test_analyze_pipeline_input_suggested_actions(mcp_client: Client):
    """Test that analysis provides helpful suggested actions."""
    test_url = "https://dev.azure.com/RussellBoley/ado-mcp/_build/results?buildId=999&view=logs"
    
    result = await mcp_client.call_tool(
        "analyze_pipeline_input",
        {"user_input": test_url}
    )
    
    analysis = result.data
    assert analysis is not None, "Analysis should not be None"
    
    # Should provide suggested next steps
    assert "suggested_action" in analysis or "next_steps" in analysis, "Should provide suggested actions"
    
    print(f"✓ Analysis includes suggested actions")


@requires_ado_creds
async def test_analyze_pipeline_input_edge_cases(mcp_client: Client):
    """Test edge cases and error handling."""
    # Test with invalid/malformed input
    test_input = "just some random text without clear pipeline reference"
    
    result = await mcp_client.call_tool(
        "analyze_pipeline_input",
        {"user_input": test_input}
    )
    
    analysis = result.data
    assert analysis is not None, "Should handle unclear input gracefully"
    
    # Should still attempt to provide some guidance
    assert isinstance(analysis, dict), "Should return dictionary even for unclear input"
    
    print(f"✓ Handles edge cases gracefully: {analysis}")


async def test_analyze_pipeline_input_tool_registration():
    """Test that the analyze_pipeline_input tool is properly registered."""
    async with Client(mcp) as client:
        tools_response = await client.list_tools()
        # Handle both potential response formats
        if hasattr(tools_response, "tools"):
            tools = tools_response.tools
        else:
            tools = tools_response
        tool_names = [tool.name for tool in tools]
        assert "analyze_pipeline_input" in tool_names, "analyze_pipeline_input tool should be registered"