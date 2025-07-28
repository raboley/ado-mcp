import os

import pytest
from fastmcp.client import Client

from server import mcp
from tests.ado.test_client import requires_ado_creds

pytestmark = pytest.mark.asyncio

TEST_PROJECT_NAME = "ado-mcp"
TEST_PIPELINE_NAME = "test_run_and_get_pipeline_run_details"


@pytest.fixture
async def mcp_client():
    async with Client(mcp) as client:
        initial_org_url = os.environ.get(
            "ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley"
        )
        await client.call_tool("set_ado_organization", {"organization_url": initial_org_url})
        yield client


@pytest.fixture
async def mcp_client_no_auth(monkeypatch):
    monkeypatch.delenv("AZURE_DEVOPS_EXT_PAT", raising=False)
    monkeypatch.delenv("ADO_ORGANIZATION_URL", raising=False)
    async with Client(mcp) as client:
        yield client


@pytest.fixture
async def completed_pipeline_run_id(mcp_client: Client):
    """Run a pipeline and wait for completion to test extraction."""
    result = await mcp_client.call_tool(
        "run_pipeline_and_get_outcome_by_name",
        {
            "project_name": TEST_PROJECT_NAME,
            "pipeline_name": TEST_PIPELINE_NAME,
            "timeout_seconds": 120,
        },
    )
    outcome = result.data
    return outcome["pipeline_run"]["id"]


@requires_ado_creds
async def test_extract_pipeline_run_data_tool_registration(mcp_client: Client):
    """Test that extraction tools are properly registered."""
    tools = await mcp_client.list_tools()
    tool_names = [tool.name for tool in tools]

    assert "extract_pipeline_run_data" in tool_names, (
        "extract_pipeline_run_data tool should be registered"
    )
    assert "extract_pipeline_run_data_by_name" in tool_names, (
        "extract_pipeline_run_data_by_name tool should be registered"
    )


@requires_ado_creds
async def test_extract_pipeline_run_data_by_name_basic_functionality(
    mcp_client: Client, completed_pipeline_run_id: int
):
    """Test basic functionality of extract_pipeline_run_data_by_name tool."""
    result = await mcp_client.call_tool(
        "extract_pipeline_run_data_by_name",
        {
            "project_name": TEST_PROJECT_NAME,
            "pipeline_name": TEST_PIPELINE_NAME,
            "run_id": completed_pipeline_run_id,
        },
    )

    extraction_data = result.data
    assert extraction_data is not None, "Expected extraction data but got None"
    assert isinstance(extraction_data, dict), f"Expected dict but got {type(extraction_data)}"

    # Verify required fields
    required_fields = [
        "run_id",
        "pipeline_name",
        "repositories",
        "variables",
        "template_parameters",
        "stages_to_skip",
    ]
    for field in required_fields:
        assert field in extraction_data, (
            f"Expected '{field}' in extraction data but got fields: {list(extraction_data.keys())}"
        )

    # Verify run ID matches
    assert extraction_data["run_id"] == completed_pipeline_run_id, (
        f"Expected run ID {completed_pipeline_run_id} but got {extraction_data['run_id']}"
    )

    # Verify pipeline name
    assert extraction_data["pipeline_name"] == TEST_PIPELINE_NAME, (
        f"Expected pipeline name '{TEST_PIPELINE_NAME}' but got '{extraction_data['pipeline_name']}'"
    )


@requires_ado_creds
async def test_extract_pipeline_run_data_repository_structure(
    mcp_client: Client, completed_pipeline_run_id: int
):
    """Test that repository data is extracted correctly."""
    result = await mcp_client.call_tool(
        "extract_pipeline_run_data_by_name",
        {
            "project_name": TEST_PROJECT_NAME,
            "pipeline_name": TEST_PIPELINE_NAME,
            "run_id": completed_pipeline_run_id,
        },
    )

    extraction_data = result.data
    repositories = extraction_data["repositories"]

    assert isinstance(repositories, list), (
        f"Expected repositories to be list but got {type(repositories)}"
    )
    assert len(repositories) > 0, "Expected at least one repository but found none"

    # Check first repository structure
    repo = repositories[0]
    repo_required_fields = ["name", "full_name", "type", "ref_name", "version"]
    for field in repo_required_fields:
        assert field in repo, (
            f"Expected '{field}' in repository data but got fields: {list(repo.keys())}"
        )

    # Verify repository data makes sense
    assert repo["name"] is not None, "Repository name should not be None"
    if repo["type"]:
        assert repo["type"] in ["gitHub", "azureReposGit", "tfvc"], (
            f"Expected valid repository type but got '{repo['type']}'"
        )


@requires_ado_creds
async def test_extract_pipeline_run_data_with_project_and_pipeline_ids(
    mcp_client: Client, completed_pipeline_run_id: int
):
    """Test extract_pipeline_run_data tool with project and pipeline IDs."""
    # Get project and pipeline IDs first
    projects_result = await mcp_client.call_tool("list_projects", {})
    projects = projects_result.data
    test_project = next(p for p in projects if p["name"] == TEST_PROJECT_NAME)
    project_id = test_project["id"]

    pipelines_result = await mcp_client.call_tool("list_pipelines", {"project_id": project_id})
    pipelines = pipelines_result.data
    test_pipeline = next(p for p in pipelines if p["name"] == TEST_PIPELINE_NAME)
    pipeline_id = test_pipeline["id"]

    # Extract using IDs
    result = await mcp_client.call_tool(
        "extract_pipeline_run_data",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "run_id": completed_pipeline_run_id,
        },
    )

    extraction_data = result.data
    assert extraction_data is not None, "Expected extraction data but got None"
    assert extraction_data["run_id"] == completed_pipeline_run_id, (
        f"Expected run ID {completed_pipeline_run_id} but got {extraction_data['run_id']}"
    )


@requires_ado_creds
async def test_extract_pipeline_run_data_fuzzy_matching(
    mcp_client: Client, completed_pipeline_run_id: int
):
    """Test that extract_pipeline_run_data_by_name supports fuzzy matching."""
    # Test with slight typos that should still match
    result = await mcp_client.call_tool(
        "extract_pipeline_run_data_by_name",
        {
            "project_name": "ado-mc",  # Missing 'p' at end
            "pipeline_name": "test_run_and_get_pipeline",  # Partial name
            "run_id": completed_pipeline_run_id,
        },
    )

    extraction_data = result.data
    assert extraction_data is not None, "Fuzzy matching should find the correct pipeline"
    assert extraction_data["run_id"] == completed_pipeline_run_id, (
        f"Expected run ID {completed_pipeline_run_id} but got {extraction_data['run_id']}"
    )


@requires_ado_creds
async def test_extract_pipeline_run_data_variables_structure(
    mcp_client: Client, completed_pipeline_run_id: int
):
    """Test that variable data is structured correctly."""
    result = await mcp_client.call_tool(
        "extract_pipeline_run_data_by_name",
        {
            "project_name": TEST_PROJECT_NAME,
            "pipeline_name": TEST_PIPELINE_NAME,
            "run_id": completed_pipeline_run_id,
        },
    )

    extraction_data = result.data
    variables = extraction_data["variables"]

    assert isinstance(variables, list), f"Expected variables to be list but got {type(variables)}"

    # Variables might be empty for simple pipelines, which is fine
    if len(variables) > 0:
        # Check variable structure if any exist
        var = variables[0]
        var_required_fields = ["name", "value", "is_secret"]
        for field in var_required_fields:
            assert field in var, (
                f"Expected '{field}' in variable data but got fields: {list(var.keys())}"
            )


@requires_ado_creds
async def test_extract_pipeline_run_data_template_parameters_structure(
    mcp_client: Client, completed_pipeline_run_id: int
):
    """Test that template parameters are structured correctly."""
    result = await mcp_client.call_tool(
        "extract_pipeline_run_data_by_name",
        {
            "project_name": TEST_PROJECT_NAME,
            "pipeline_name": TEST_PIPELINE_NAME,
            "run_id": completed_pipeline_run_id,
        },
    )

    extraction_data = result.data
    template_parameters = extraction_data["template_parameters"]

    assert isinstance(template_parameters, dict), (
        f"Expected template_parameters to be dict but got {type(template_parameters)}"
    )

    # Template parameters might be empty since they're not preserved in run details
    # This is expected behavior as noted in the implementation


async def test_extract_pipeline_run_data_no_authentication(mcp_client_no_auth: Client):
    """Test extract pipeline tools fail gracefully without authentication."""
    from fastmcp.exceptions import ToolError

    with pytest.raises(ToolError):  # Should raise a ToolError when no auth is available
        await mcp_client_no_auth.call_tool(
            "extract_pipeline_run_data_by_name",
            {
                "project_name": TEST_PROJECT_NAME,
                "pipeline_name": TEST_PIPELINE_NAME,
                "run_id": 12345,
            },
        )


@requires_ado_creds
async def test_extract_pipeline_run_data_nonexistent_run_id(mcp_client: Client):
    """Test extract pipeline tools with a non-existent run ID."""
    from fastmcp.exceptions import ToolError

    with pytest.raises(ToolError):  # Should raise a ToolError for non-existent run
        await mcp_client.call_tool(
            "extract_pipeline_run_data_by_name",
            {
                "project_name": TEST_PROJECT_NAME,
                "pipeline_name": TEST_PIPELINE_NAME,
                "run_id": 999999999,  # Non-existent run ID
            },
        )


@requires_ado_creds
async def test_extract_pipeline_run_data_validates_outcome_structure(
    mcp_client: Client, completed_pipeline_run_id: int
):
    """Test that extract_pipeline_run_data returns properly structured data."""
    result = await mcp_client.call_tool(
        "extract_pipeline_run_data_by_name",
        {
            "project_name": TEST_PROJECT_NAME,
            "pipeline_name": TEST_PIPELINE_NAME,
            "run_id": completed_pipeline_run_id,
        },
    )

    extraction_data = result.data

    # Validate required fields
    required_fields = [
        "run_id",
        "pipeline_name",
        "repositories",
        "variables",
        "template_parameters",
        "stages_to_skip",
    ]
    for field in required_fields:
        assert field in extraction_data, (
            f"Expected '{field}' in extraction data but got fields: {list(extraction_data.keys())}"
        )

    # Validate types
    assert isinstance(extraction_data["run_id"], int), (
        f"Expected int run_id but got {type(extraction_data['run_id'])}"
    )
    assert isinstance(extraction_data["repositories"], list), (
        f"Expected list repositories but got {type(extraction_data['repositories'])}"
    )
    assert isinstance(extraction_data["variables"], list), (
        f"Expected list variables but got {type(extraction_data['variables'])}"
    )
    assert isinstance(extraction_data["template_parameters"], dict), (
        f"Expected dict template_parameters but got {type(extraction_data['template_parameters'])}"
    )
    assert isinstance(extraction_data["stages_to_skip"], list), (
        f"Expected list stages_to_skip but got {type(extraction_data['stages_to_skip'])}"
    )

    # Validate pipeline_name type (can be None)
    pipeline_name = extraction_data["pipeline_name"]
    assert pipeline_name is None or isinstance(pipeline_name, str), (
        f"Expected None or str pipeline_name but got {type(pipeline_name)}"
    )
