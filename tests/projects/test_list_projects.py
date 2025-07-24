import os

import pytest
from fastmcp.client import Client

from server import mcp
from src.test_config import get_project_id, get_project_name
from tests.ado.test_client import requires_ado_creds

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
async def test_list_projects_returns_valid_list(mcp_client: Client):
    result = await mcp_client.call_tool("list_projects")

    projects = result.data
    assert projects is not None, f"Expected projects list to exist, but got {projects}"
    assert isinstance(projects, list), f"Expected projects to be a list, but got {type(projects)}"

    if len(projects) > 0:
        project = projects[0]
        assert isinstance(project, dict), (
            f"Expected project to be a dictionary, but got {type(project)}"
        )
        assert "id" in project, (
            f"Expected project to have 'id' field, but got keys: {list(project.keys())}"
        )
        assert "name" in project, (
            f"Expected project to have 'name' field, but got keys: {list(project.keys())}"
        )
        assert "url" in project, (
            f"Expected project to have 'url' field, but got keys: {list(project.keys())}"
        )

        assert isinstance(project["id"], str), (
            f"Expected project id to be a string, but got {type(project['id'])}: {project['id']}"
        )
        assert isinstance(project["name"], str), (
            f"Expected project name to be a string, but got {type(project['name'])}: {project['name']}"
        )
        assert isinstance(project["url"], str), (
            f"Expected project url to be a string, but got {type(project['url'])}: {project['url']}"
        )


@requires_ado_creds
async def test_list_projects_finds_expected_project(mcp_client: Client):
    result = await mcp_client.call_tool("list_projects")

    projects = result.data
    assert isinstance(projects, list), f"Expected projects to be a list, but got {type(projects)}"

    expected_project_name = get_project_name()
    ado_mcp_project = None
    project_names = []
    for project in projects:
        project_names.append(project.get("name"))
        if project.get("name") == expected_project_name:
            ado_mcp_project = project
            break

    assert ado_mcp_project is not None, (
        f"Expected to find '{expected_project_name}' project, but found projects: {project_names}"
    )
    expected_project_id = get_project_id()
    assert ado_mcp_project["id"] == expected_project_id, (
        f"Expected project ID '{expected_project_id}', but got '{ado_mcp_project['id']}'"
    )


async def test_list_projects_tool_registration():
    async with Client(mcp) as client:
        tools_response = await client.list_tools()
        if hasattr(tools_response, "tools"):
            tools = tools_response.tools
        else:
            tools = tools_response
        tool_names = [tool.name for tool in tools]
        assert "list_projects" in tool_names, (
            f"Expected 'list_projects' tool to be registered, but found tools: {tool_names}"
        )
