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
async def test_analyze_pipeline_input_with_url(mcp_client: Client):
    """Test analyzing pipeline input with Azure DevOps URL."""
    test_url = "https://dev.azure.com/RussellBoley/ado-mcp/_build/results?buildId=324&view=results"

    result = await mcp_client.call_tool("analyze_pipeline_input", {"user_input": test_url})

    analysis = result.data
    assert analysis is not None, "Analysis should not be None"
    assert isinstance(analysis, dict), "Analysis should be a dictionary"

    # Verify analysis structure
    assert "input_type" in analysis, "Analysis should have input_type"
    assert "extracted_info" in analysis, "Analysis should have extracted_info"
    assert "next_steps" in analysis, "Analysis should have next_steps"
    assert "confidence" in analysis, "Analysis should have confidence"

    # Check URL parsing results
    assert analysis["input_type"] == "azure_devops_url", "Should identify as Azure DevOps URL"
    assert analysis["confidence"] == "high", "Should have high confidence for clear URL"

    extracted = analysis["extracted_info"]
    assert extracted["organization"] == "RussellBoley", "Should extract correct organization"
    assert extracted["project"] == "ado-mcp", "Should extract correct project"
    assert extracted["build_id"] == 324, "Should extract correct build ID"
    assert extracted["url_type"] == "build_results", "Should identify as build results URL"

    # Check next steps guidance
    assert len(analysis["next_steps"]) > 0, "Should provide next steps"
    assert any("get_build_by_id" in step for step in analysis["next_steps"]), (
        "Should suggest get_build_by_id"
    )

    print(
        f"✓ Successfully analyzed URL: {analysis['input_type']} with {analysis['confidence']} confidence"
    )


@requires_ado_creds
async def test_analyze_pipeline_input_with_pipeline_name(mcp_client: Client):
    """Test analyzing pipeline input with pipeline name."""

    result = await mcp_client.call_tool(
        "analyze_pipeline_input", {"user_input": "log-test-complex pipeline failed"}
    )

    analysis = result.data
    assert analysis is not None, "Analysis should not be None"

    # Should identify pipeline name in text
    assert "input_type" in analysis, "Should have input_type"
    extracted = analysis["extracted_info"]

    # Check that it found potential pipeline names
    assert "pipeline_names" in extracted, "Should extract pipeline names"
    assert len(analysis["next_steps"]) > 0, "Should provide guidance"

    print(f"✓ Successfully analyzed text input: {analysis['input_type']}")


@requires_ado_creds
async def test_find_pipeline_by_name_exact_match(mcp_client: Client):
    """Test finding pipeline by exact name match."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project

    result = await mcp_client.call_tool(
        "find_pipeline_by_name",
        {"pipeline_name": "log-test-complex", "project_id": project_id, "exact_match": True},
    )

    search_result = result.data
    assert search_result is not None, "Search result should not be None"
    assert isinstance(search_result, dict), "Search result should be a dictionary"

    # Verify search result structure
    assert "search_term" in search_result, "Should have search_term"
    assert "total_matches" in search_result, "Should have total_matches"
    assert "matches" in search_result, "Should have matches"
    assert "suggested_actions" in search_result, "Should have suggested_actions"

    # Should find exact match
    assert search_result["total_matches"] >= 1, "Should find at least one match"

    if search_result["matches"]:
        best_match = search_result["matches"][0]
        assert "pipeline" in best_match, "Match should have pipeline info"
        assert "match_type" in best_match, "Match should have match_type"
        assert "confidence" in best_match, "Match should have confidence"
        assert best_match["match_type"] == "exact", "Should be exact match"
        assert best_match["confidence"] == 1.0, "Exact match should have confidence 1.0"
        assert best_match["pipeline"]["name"] == "log-test-complex", "Should match exact name"

    print(f"✓ Found {search_result['total_matches']} matches for exact search")


@requires_ado_creds
async def test_find_pipeline_by_name_fuzzy_match(mcp_client: Client):
    """Test finding pipeline by fuzzy name matching."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project

    result = await mcp_client.call_tool(
        "find_pipeline_by_name",
        {
            "pipeline_name": "test-complex",  # Partial name
            "project_id": project_id,
            "exact_match": False,
        },
    )

    search_result = result.data
    assert search_result is not None, "Search result should not be None"

    # Should find fuzzy matches
    assert search_result["total_matches"] >= 1, "Should find at least one fuzzy match"

    if search_result["matches"]:
        # Check that confidence scoring works
        for match in search_result["matches"]:
            assert 0.0 < match["confidence"] <= 1.0, "Confidence should be between 0 and 1"
            assert match["match_type"] in ["exact", "contains", "contained_in", "word_match"], (
                "Should have valid match type"
            )

    print(f"✓ Found {search_result['total_matches']} fuzzy matches")


@requires_ado_creds
async def test_resolve_pipeline_from_url_build_results(mcp_client: Client):
    """Test complete pipeline resolution from build results URL."""
    test_url = "https://dev.azure.com/RussellBoley/ado-mcp/_build/results?buildId=324&view=results"

    result = await mcp_client.call_tool("resolve_pipeline_from_url", {"url": test_url})

    resolution = result.data
    assert resolution is not None, "Resolution should not be None"
    assert isinstance(resolution, dict), "Resolution should be a dictionary"

    # Verify complete resolution
    assert "url_info" in resolution, "Should have parsed URL info"
    assert "project_id" in resolution, "Should have resolved project_id"
    assert "project_name" in resolution, "Should have project name"
    assert "organization" in resolution, "Should have organization"

    # For build results URL, should have build and pipeline info
    assert "build_id" in resolution, "Should have build_id"
    assert "pipeline_id" in resolution, "Should have pipeline_id"
    assert "pipeline_name" in resolution, "Should have pipeline_name"
    assert "suggested_actions" in resolution, "Should have suggested_actions"

    # Verify specific values for test URL
    assert resolution["project_name"] == "ado-mcp", "Should resolve correct project"
    assert resolution["build_id"] == 324, "Should extract correct build_id"
    assert resolution["pipeline_id"] == 84, "Should resolve correct pipeline_id"
    assert resolution["pipeline_name"] == "log-test-complex", "Should resolve correct pipeline name"

    # Check suggested actions
    assert len(resolution["suggested_actions"]) > 0, "Should provide suggested actions"
    assert any("get_pipeline_run" in action for action in resolution["suggested_actions"]), (
        "Should suggest get_pipeline_run"
    )

    print(f"✓ Resolved URL to pipeline {resolution['pipeline_id']} ({resolution['pipeline_name']})")


@requires_ado_creds
async def test_helper_tools_tool_registration(mcp_client: Client):
    """Test that helper tools are properly registered."""
    # List available tools
    tools_response = await mcp_client.list_tools()

    # Handle both potential response formats
    if hasattr(tools_response, "tools"):
        tools = tools_response.tools
    else:
        tools = tools_response

    tool_names = [tool.name for tool in tools]

    # Check that helper tools are registered
    expected_tools = [
        "analyze_pipeline_input",
        "find_pipeline_by_name",
        "resolve_pipeline_from_url",
    ]

    for tool_name in expected_tools:
        assert tool_name in tool_names, f"{tool_name} tool should be registered"

    # Verify analyze_pipeline_input tool details
    analyze_tool = next(tool for tool in tools if tool.name == "analyze_pipeline_input")
    assert "Intelligently analyze user input" in analyze_tool.description, (
        "Should have descriptive description"
    )

    # Verify input schema
    input_schema = analyze_tool.inputSchema
    assert "user_input" in input_schema["properties"], "Should have user_input parameter"
    assert "organization" in input_schema["properties"], (
        "Should have optional organization parameter"
    )
    assert "project" in input_schema["properties"], "Should have optional project parameter"

    print(f"✓ All {len(expected_tools)} helper tools properly registered")


@pytest.fixture
async def mcp_client_with_unset_ado_env(monkeypatch):
    """
    Provides a client for tests where ADO env vars are unset,
    simulating a server startup without initial credentials.
    """
    monkeypatch.delenv("ADO_ORGANIZATION_URL", raising=False)
    monkeypatch.delenv("AZURE_DEVOPS_EXT_PAT", raising=False)
    import importlib

    import server

    importlib.reload(server)
    async with Client(server.mcp) as client:
        yield client


async def test_helper_tools_no_client(mcp_client_with_unset_ado_env: Client):
    """Test helper tools behavior when no client is available."""
    result = await mcp_client_with_unset_ado_env.call_tool(
        "analyze_pipeline_input", {"user_input": "test"}
    )

    analysis = result.data
    assert "error" in analysis, "Should return error when no client available"
    assert "ADO client not available" in analysis["error"], "Should indicate client unavailable"
    assert "suggestion" in analysis, "Should provide suggestion"

    print("✓ Helper tools properly handle no client scenario")


@requires_ado_creds
async def test_analyze_pipeline_input_with_yaml_file(mcp_client: Client):
    """Test analyzing input that mentions YAML files."""

    result = await mcp_client.call_tool(
        "analyze_pipeline_input",
        {"user_input": "The pipeline uses azure-pipelines.yml file and it's failing"},
    )

    analysis = result.data
    assert analysis is not None, "Analysis should not be None"

    extracted = analysis["extracted_info"]
    assert "yaml_files" in extracted, "Should extract YAML files"
    assert len(extracted["yaml_files"]) > 0, "Should find YAML file references"
    assert "azure-pipelines.yml" in extracted["yaml_files"], "Should find specific YAML file"

    # Should identify as YAML reference input
    assert analysis["input_type"] in ["yaml_reference", "text_with_urls"], (
        "Should identify YAML reference type"
    )

    print(f"✓ Successfully identified YAML file: {extracted['yaml_files']}")
