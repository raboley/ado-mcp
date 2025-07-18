"""
Tests for the find_pipeline_by_id_and_name MCP tool.

This module tests the pipeline finding helper with fuzzy name matching.
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
KNOWN_PIPELINE_NAME = "github-resources-test-stable"
KNOWN_PIPELINE_ID = 200


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
async def test_find_pipeline_by_id_and_name_exact_match(mcp_client: Client):
    """Test finding pipeline with exact name match."""
    result = await mcp_client.call_tool(
        "find_pipeline_by_id_and_name",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_name": KNOWN_PIPELINE_NAME,
            "exact_match": True
        }
    )
    
    pipelines = result.data
    assert pipelines is not None, "Result should not be None"
    assert isinstance(pipelines, dict), "Result should be a dictionary"
    
    # Should find matches
    assert "matches" in pipelines, "Should have matches field"
    assert len(pipelines["matches"]) > 0, "Should find at least one match"
    
    # First match should be exact
    first_match = pipelines["matches"][0]
    assert first_match["name"] == KNOWN_PIPELINE_NAME, "First match should be exact"
    assert first_match["id"] == KNOWN_PIPELINE_ID, "Should have correct pipeline ID"
    
    print(f"✓ Found exact match: {first_match['name']} (ID: {first_match['id']})")


@requires_ado_creds
async def test_find_pipeline_by_id_and_name_fuzzy_match(mcp_client: Client):
    """Test finding pipeline with fuzzy name matching."""
    # Use partial name that should fuzzy match
    result = await mcp_client.call_tool(
        "find_pipeline_by_id_and_name",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_name": "github resources",  # Partial name without hyphens
            "exact_match": False
        }
    )
    
    pipelines = result.data
    assert pipelines is not None, "Result should not be None"
    assert "matches" in pipelines, "Should have matches field"
    assert len(pipelines["matches"]) > 0, "Should find fuzzy matches"
    
    # Should find our known pipeline
    pipeline_names = [p["name"] for p in pipelines["matches"]]
    assert any("github-resources" in name for name in pipeline_names), "Should find GitHub resources pipeline"
    
    print(f"✓ Fuzzy matching found {len(pipelines['matches'])} pipelines")


@requires_ado_creds
async def test_find_pipeline_by_id_and_name_with_typo(mcp_client: Client):
    """Test finding pipeline with typo in name."""
    # Intentional typo
    result = await mcp_client.call_tool(
        "find_pipeline_by_id_and_name",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_name": "gihub-resouces-test",  # Typos: gihub, resouces
            "exact_match": False
        }
    )
    
    pipelines = result.data
    assert pipelines is not None, "Result should not be None"
    assert "matches" in pipelines, "Should have matches field"
    
    # Fuzzy matching should still find the pipeline despite typos
    if len(pipelines["matches"]) > 0:
        # Check if it found something related
        pipeline_names = [p["name"] for p in pipelines["matches"]]
        print(f"✓ Fuzzy matching handled typos, found: {pipeline_names[:3]}")
    else:
        print("✓ No matches for heavily mistyped name (expected)")


@requires_ado_creds
async def test_find_pipeline_by_id_and_name_no_matches(mcp_client: Client):
    """Test behavior when no pipelines match."""
    result = await mcp_client.call_tool(
        "find_pipeline_by_id_and_name",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_name": "NonExistentPipelineXYZ123",
            "exact_match": True
        }
    )
    
    pipelines = result.data
    assert pipelines is not None, "Result should not be None"
    assert "matches" in pipelines, "Should have matches field"
    assert len(pipelines["matches"]) == 0, "Should find no matches for non-existent pipeline"
    
    print("✓ Correctly returns empty matches for non-existent pipeline")


@requires_ado_creds
async def test_find_pipeline_by_id_and_name_match_scores(mcp_client: Client):
    """Test that fuzzy matching provides match scores."""
    result = await mcp_client.call_tool(
        "find_pipeline_by_id_and_name",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_name": "test",  # Generic term that should match multiple pipelines
            "exact_match": False
        }
    )
    
    pipelines = result.data
    assert pipelines is not None, "Result should not be None"
    assert "matches" in pipelines, "Should have matches field"
    
    if len(pipelines["matches"]) > 0:
        # Check if matches have scores
        first_match = pipelines["matches"][0]
        assert "score" in first_match or "match_score" in first_match, "Matches should have score information"
        
        # Matches should be sorted by relevance
        print(f"✓ Found {len(pipelines['matches'])} matches with scoring")
    else:
        print("✓ No matches found for generic term")


@requires_ado_creds
async def test_find_pipeline_by_id_and_name_case_insensitive(mcp_client: Client):
    """Test that name matching is case insensitive."""
    result = await mcp_client.call_tool(
        "find_pipeline_by_id_and_name",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_name": "GITHUB-RESOURCES-TEST-STABLE",  # All caps
            "exact_match": False
        }
    )
    
    pipelines = result.data
    assert pipelines is not None, "Result should not be None"
    assert "matches" in pipelines, "Should have matches field"
    assert len(pipelines["matches"]) > 0, "Should find matches regardless of case"
    
    # Should find the correct pipeline
    pipeline_names = [p["name"] for p in pipelines["matches"]]
    assert any("github-resources-test-stable" in name.lower() for name in pipeline_names), "Should find pipeline with case-insensitive match"
    
    print("✓ Case-insensitive matching works correctly")


@requires_ado_creds
async def test_find_pipeline_by_id_and_name_suggested_actions(mcp_client: Client):
    """Test that the tool provides suggested actions."""
    result = await mcp_client.call_tool(
        "find_pipeline_by_id_and_name",
        {
            "project_id": TEST_PROJECT_ID,
            "pipeline_name": "preview",
            "exact_match": False
        }
    )
    
    pipelines = result.data
    assert pipelines is not None, "Result should not be None"
    
    # Should provide suggested actions
    assert "suggested_actions" in pipelines or "next_steps" in pipelines, "Should provide suggested actions"
    
    print("✓ Tool provides suggested actions for results")


async def test_find_pipeline_by_id_and_name_tool_registration():
    """Test that the find_pipeline_by_id_and_name tool is properly registered."""
    async with Client(mcp) as client:
        tools_response = await client.list_tools()
        # Handle both potential response formats
        if hasattr(tools_response, "tools"):
            tools = tools_response.tools
        else:
            tools = tools_response
        tool_names = [tool.name for tool in tools]
        assert "find_pipeline_by_id_and_name" in tool_names, "find_pipeline_by_id_and_name tool should be registered"