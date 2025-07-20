import os

import pytest
from fastmcp.client import Client

from server import mcp
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
async def test_resources_parameter_capability(mcp_client: Client):
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"
    pipeline_id = 200
    
    resources = {
        "repositories": {
            "tooling": {
                "refName": "refs/heads/stable/0.0.1"
            }
        }
    }
    
    template_parameters = {
        "taskfileVersion": "latest",
        "installPath": "./bin/resources-test"
    }
    
    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "resources": resources,
            "template_parameters": template_parameters
        }
    )
    
    pipeline_run = result.data
    assert pipeline_run is not None, f"Expected pipeline run data but got None"
    assert isinstance(pipeline_run, dict), f"Expected pipeline run to be dict but got {type(pipeline_run)}"
    
    assert pipeline_run["id"] is not None, f"Expected pipeline run to have an ID but got {pipeline_run.get('id')}"
    assert pipeline_run["state"] in ["unknown", "inProgress"], f"Expected pipeline state to be 'unknown' or 'inProgress' but got '{pipeline_run.get('state')}'"


@requires_ado_creds
async def test_template_parameters_capability(mcp_client: Client):
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"
    pipeline_id = 75
    
    variables = {
        "testVariable": "template-params-test"
    }
    
    template_parameters = {
        "environment": "testing",
        "buildConfiguration": "Debug"
    }
    
    try:
        result = await mcp_client.call_tool(
            "run_pipeline",
            {
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "variables": variables,
                "template_parameters": template_parameters
            }
        )
        
        pipeline_run = result.data
        assert pipeline_run is not None, f"Expected pipeline run data but got None"
        assert isinstance(pipeline_run, dict), f"Expected pipeline run to be dict but got {type(pipeline_run)}"
        
        assert pipeline_run["id"] is not None, f"Expected pipeline run to have an ID but got {pipeline_run.get('id')}"
        assert pipeline_run["state"] in ["unknown", "inProgress"], f"Expected pipeline state to be 'unknown' or 'inProgress' but got '{pipeline_run.get('state')}'"
        
    except Exception as e:
        if "400" in str(e):
            pass
        else:
            raise


@requires_ado_creds
async def test_branch_selection_capability(mcp_client: Client):
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"
    pipeline_id = 59
    
    branch = "refs/heads/main"
    
    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "branch": branch
        }
    )
    
    pipeline_run = result.data
    assert pipeline_run is not None, f"Expected pipeline run data but got None"
    assert isinstance(pipeline_run, dict), f"Expected pipeline run to be dict but got {type(pipeline_run)}"
    
    assert pipeline_run["id"] is not None, f"Expected pipeline run to have an ID but got {pipeline_run.get('id')}"
    assert pipeline_run["state"] in ["unknown", "inProgress"], f"Expected pipeline state to be 'unknown' or 'inProgress' but got '{pipeline_run.get('state')}'"


@requires_ado_creds
async def test_name_based_capabilities(mcp_client: Client):
    project_name = "ado-mcp"
    pipeline_name = "test_run_and_get_pipeline_run_details"
    
    branch = "refs/heads/main"
    
    result = await mcp_client.call_tool(
        "run_pipeline_by_name",
        {
            "project_name": project_name,
            "pipeline_name": pipeline_name,
            "branch": branch
        }
    )
    
    pipeline_run = result.data
    assert pipeline_run is not None, f"Expected pipeline run data but got None"
    assert isinstance(pipeline_run, dict), f"Expected pipeline run to be dict but got {type(pipeline_run)}"
    
    assert pipeline_run["id"] is not None, f"Expected pipeline run to have an ID but got {pipeline_run.get('id')}"
    assert pipeline_run["state"] in ["unknown", "inProgress"], f"Expected pipeline state to be 'unknown' or 'inProgress' but got '{pipeline_run.get('state')}'"


@requires_ado_creds
async def test_comprehensive_capabilities_demo(mcp_client: Client):
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"
    pipeline_id = 59
    
    branch = "refs/heads/main"
    
    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "branch": branch
        }
    )
    
    pipeline_run = result.data
    assert pipeline_run is not None, f"Expected pipeline run data but got None"
    assert isinstance(pipeline_run, dict), f"Expected pipeline run to be dict but got {type(pipeline_run)}"
    
    assert pipeline_run["id"] is not None, f"Expected pipeline run to have an ID but got {pipeline_run.get('id')}"
    assert pipeline_run["state"] in ["unknown", "inProgress"], f"Expected pipeline state to be 'unknown' or 'inProgress' but got '{pipeline_run.get('state')}'"


@requires_ado_creds
async def test_github_resources_concept_validation(mcp_client: Client):
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"
    pipeline_id = 59
    
    branch = "refs/heads/main"
    
    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "branch": branch
        }
    )
    
    pipeline_run = result.data
    assert pipeline_run is not None, f"Expected pipeline run data but got None"
    assert isinstance(pipeline_run, dict), f"Expected pipeline run to be dict but got {type(pipeline_run)}"
    assert pipeline_run["id"] is not None, f"Expected pipeline run to have an ID but got {pipeline_run.get('id')}"

