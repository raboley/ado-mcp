import os

import pytest
from fastmcp.client import Client

from server import mcp
from src.test_config import get_project_id, get_project_name
from tests.ado.test_client import requires_ado_creds

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio


async def get_pipeline_id_by_name(mcp_client: Client, pipeline_name: str) -> int:
    """
    Helper function to get pipeline ID by name.

    Args:
        mcp_client: MCP client instance
        pipeline_name: Name of the pipeline to find

    Returns:
        Pipeline ID as integer

    Raises:
        AssertionError: If pipeline not found or lookup fails
    """
    get_project_id()

    result = await mcp_client.call_tool(
        "find_pipeline_by_name",
        {"project_name": get_project_name(), "pipeline_name": pipeline_name},
    )

    pipeline_info = result.data
    assert pipeline_info is not None, f"Failed to find pipeline '{pipeline_name}'"
    assert "pipeline" in pipeline_info, (
        f"Pipeline info should contain pipeline key but got: {pipeline_info}"
    )
    assert "id" in pipeline_info["pipeline"], (
        f"Pipeline should have ID but got: {pipeline_info['pipeline']}"
    )

    return pipeline_info["pipeline"]["id"]


@pytest.fixture
async def mcp_client():
    async with Client(mcp) as client:
        initial_org_url = os.environ.get(
            "ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley"
        )
        await client.call_tool("set_ado_organization", {"organization_url": initial_org_url})
        yield client


@requires_ado_creds
async def test_analyze_pipeline_input_with_url(mcp_client: Client):
    # Use a sample build ID URL for testing URL parsing (doesn't need to exist)
    test_url = (
        "https://dev.azure.com/RussellBoley/ado-mcp/_build/results?buildId=12345&view=results"
    )

    result = await mcp_client.call_tool("analyze_pipeline_input", {"user_input": test_url})

    analysis = result.data
    assert analysis is not None, f"Analysis should not be None but got {analysis}"
    assert isinstance(analysis, dict), f"Analysis should be a dictionary but got {type(analysis)}"

    assert "input_type" in analysis, (
        f"Analysis should have input_type but got keys: {list(analysis.keys())}"
    )
    assert "extracted_info" in analysis, (
        f"Analysis should have extracted_info but got keys: {list(analysis.keys())}"
    )
    assert "next_steps" in analysis, (
        f"Analysis should have next_steps but got keys: {list(analysis.keys())}"
    )
    assert "confidence" in analysis, (
        f"Analysis should have confidence but got keys: {list(analysis.keys())}"
    )

    assert analysis["input_type"] == "azure_devops_url", (
        f"Should identify as Azure DevOps URL but got '{analysis['input_type']}'"
    )
    assert analysis["confidence"] == "high", (
        f"Should have high confidence for clear URL but got '{analysis['confidence']}'"
    )

    extracted = analysis["extracted_info"]
    assert extracted["organization"] == "RussellBoley", (
        f"Should extract correct organization but got '{extracted['organization']}'"
    )
    assert extracted["project"] == "ado-mcp", (
        f"Should extract correct project but got '{extracted['project']}'"
    )
    assert extracted["build_id"] == 12345, (
        f"Should extract correct build ID but got {extracted['build_id']}"
    )
    assert extracted["url_type"] == "build_results", (
        f"Should identify as build results URL but got '{extracted['url_type']}'"
    )

    assert len(analysis["next_steps"]) > 0, (
        f"Should provide next steps but got {len(analysis['next_steps'])} steps"
    )
    assert any("get_build_by_id" in step for step in analysis["next_steps"]), (
        f"Should suggest get_build_by_id but got steps: {analysis['next_steps']}"
    )


@requires_ado_creds
async def test_analyze_pipeline_input_with_pipeline_name(mcp_client: Client):
    result = await mcp_client.call_tool(
        "analyze_pipeline_input", {"user_input": "log-test-complex pipeline failed"}
    )

    analysis = result.data
    assert analysis is not None, f"Analysis should not be None but got {analysis}"

    assert "input_type" in analysis, f"Should have input_type but got keys: {list(analysis.keys())}"
    extracted = analysis["extracted_info"]

    assert "pipeline_names" in extracted, (
        f"Should extract pipeline names but got keys: {list(extracted.keys())}"
    )
    assert len(analysis["next_steps"]) > 0, (
        f"Should provide guidance but got {len(analysis['next_steps'])} steps"
    )


@requires_ado_creds
async def test_find_pipeline_by_name_exact_match(mcp_client: Client):
    project_id = get_project_id()

    result = await mcp_client.call_tool(
        "find_pipeline_by_id_and_name",
        {"pipeline_name": "slow.log-test-complex", "project_id": project_id, "exact_match": True},
    )

    search_result = result.data
    assert search_result is not None, f"Search result should not be None but got {search_result}"
    assert isinstance(search_result, dict), (
        f"Search result should be a dictionary but got {type(search_result)}"
    )

    # Verify search result structure
    assert "search_term" in search_result, (
        f"Should have search_term but got keys: {list(search_result.keys())}"
    )
    assert "total_matches" in search_result, (
        f"Should have total_matches but got keys: {list(search_result.keys())}"
    )
    assert "matches" in search_result, (
        f"Should have matches but got keys: {list(search_result.keys())}"
    )
    assert "suggested_actions" in search_result, (
        f"Should have suggested_actions but got keys: {list(search_result.keys())}"
    )

    assert search_result["total_matches"] >= 1, (
        f"Should find at least one match but got {search_result['total_matches']} matches"
    )

    if search_result["matches"]:
        best_match = search_result["matches"][0]
        assert "pipeline" in best_match, (
            f"Match should have pipeline info but got keys: {list(best_match.keys())}"
        )
        assert "match_type" in best_match, (
            f"Match should have match_type but got keys: {list(best_match.keys())}"
        )
        assert "confidence" in best_match, (
            f"Match should have confidence but got keys: {list(best_match.keys())}"
        )
        assert best_match["match_type"] == "exact", (
            f"Should be exact match but got '{best_match['match_type']}'"
        )
        assert best_match["confidence"] == 1.0, (
            f"Exact match should have confidence 1.0 but got {best_match['confidence']}"
        )
        assert best_match["pipeline"]["name"] == "slow.log-test-complex", (
            f"Should match exact name but got '{best_match['pipeline']['name']}'"
        )


@requires_ado_creds
async def test_find_pipeline_by_name_fuzzy_match(mcp_client: Client):
    project_id = get_project_id()

    result = await mcp_client.call_tool(
        "find_pipeline_by_id_and_name",
        {
            "pipeline_name": "test-complex",
            "project_id": project_id,
            "exact_match": False,
        },
    )

    search_result = result.data
    assert search_result is not None, f"Search result should not be None but got {search_result}"

    assert search_result["total_matches"] >= 1, (
        f"Should find at least one fuzzy match but got {search_result['total_matches']} matches"
    )

    if search_result["matches"]:
        for match in search_result["matches"]:
            assert 0.0 < match["confidence"] <= 1.0, (
                f"Confidence should be between 0 and 1 but got {match['confidence']}"
            )
            assert match["match_type"] in ["exact", "contains", "contained_in", "word_match"], (
                f"Should have valid match type but got '{match['match_type']}'"
            )


@requires_ado_creds
async def test_resolve_pipeline_from_url_build_results(mcp_client: Client):
    # First create a real build to get a valid URL structure
    project_name = get_project_name()
    pipeline_name = "test_run_and_get_pipeline_run_details"

    # Run a pipeline to get a real build ID
    run_result = await mcp_client.call_tool(
        "run_pipeline_by_name", {"project_name": project_name, "pipeline_name": pipeline_name}
    )

    pipeline_run = run_result.data
    build_id = pipeline_run["id"]

    # Create the URL with the real build ID and correct project name
    test_url = f"https://dev.azure.com/RussellBoley/{project_name}/_build/results?buildId={build_id}&view=results"

    result = await mcp_client.call_tool("resolve_pipeline_from_url", {"url": test_url})

    resolution = result.data
    assert resolution is not None, "Resolution should not be None"
    assert isinstance(resolution, dict), "Resolution should be a dictionary"

    assert "url_info" in resolution, "Should have parsed URL info"
    assert "project_id" in resolution, "Should have resolved project_id"
    assert "project_name" in resolution, "Should have project name"
    assert "organization" in resolution, "Should have organization"

    assert "build_id" in resolution, "Should have build_id"
    assert "pipeline_id" in resolution, "Should have pipeline_id"
    assert "pipeline_name" in resolution, "Should have pipeline_name"
    assert "suggested_actions" in resolution, "Should have suggested_actions"

    assert resolution["project_name"] == project_name, (
        f"Should resolve correct project {project_name}"
    )
    assert resolution["build_id"] == build_id, f"Should extract correct build_id {build_id}"
    assert resolution["pipeline_name"] == pipeline_name, "Should resolve correct pipeline name"

    assert len(resolution["suggested_actions"]) > 0, "Should provide suggested actions"
    assert any("get_pipeline_run" in action for action in resolution["suggested_actions"]), (
        "Should suggest get_pipeline_run"
    )


@requires_ado_creds
async def test_helper_tools_tool_registration(mcp_client: Client):
    tools_response = await mcp_client.list_tools()

    if hasattr(tools_response, "tools"):
        tools = tools_response.tools
    else:
        tools = tools_response

    tool_names = [tool.name for tool in tools]

    expected_tools = [
        "analyze_pipeline_input",
        "find_pipeline_by_name",
        "resolve_pipeline_from_url",
    ]

    for tool_name in expected_tools:
        assert tool_name in tool_names, f"{tool_name} tool should be registered"

    analyze_tool = next(tool for tool in tools if tool.name == "analyze_pipeline_input")
    assert "Intelligently analyze user input" in analyze_tool.description, (
        "Should have descriptive description"
    )

    input_schema = analyze_tool.inputSchema
    assert "user_input" in input_schema["properties"], "Should have user_input parameter"
    assert "organization" in input_schema["properties"], (
        "Should have optional organization parameter"
    )
    assert "project" in input_schema["properties"], "Should have optional project parameter"


@pytest.fixture
async def mcp_client_with_unset_ado_env(monkeypatch):
    monkeypatch.delenv("ADO_ORGANIZATION_URL", raising=False)
    monkeypatch.delenv("AZURE_DEVOPS_EXT_PAT", raising=False)
    import importlib

    import server

    importlib.reload(server)
    async with Client(server.mcp) as client:
        yield client


async def test_helper_tools_no_client(mcp_client_with_unset_ado_env: Client):
    result = await mcp_client_with_unset_ado_env.call_tool(
        "analyze_pipeline_input", {"user_input": "test"}
    )

    analysis = result.data
    assert "error" in analysis, "Should return error when no client available"
    assert "ADO client not available" in analysis["error"], "Should indicate client unavailable"
    assert "suggestion" in analysis, "Should provide suggestion"


@requires_ado_creds
async def test_analyze_pipeline_input_with_yaml_file(mcp_client: Client):
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

    assert analysis["input_type"] in ["yaml_reference", "text_with_urls"], (
        "Should identify YAML reference type"
    )
