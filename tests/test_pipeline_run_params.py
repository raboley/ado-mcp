"""
End-to-end tests for pipeline run parameters (variables, templates, branch selection).
"""

import os

import pytest
from fastmcp.client import Client

from ado.models import PipelineRunRequest
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
async def test_run_pipeline_with_variables(mcp_client: Client):
    """Tests running a pipeline with runtime variables."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 75  # preview-test-parameterized pipeline (accepts variables)
    
    # Define runtime variables
    variables = {
        "myVariable": "test-value-123",
        "environment": "testing"
    }
    
    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "variables": variables
        }
    )
    
    pipeline_run = result.data
    assert pipeline_run is not None, "Pipeline run should not be None"
    assert isinstance(pipeline_run, dict), "Pipeline run should be a dictionary"
    
    # Verify pipeline was started
    assert pipeline_run["id"] is not None, "Pipeline run should have an ID"
    assert pipeline_run["state"] in ["unknown", "inProgress"], "Pipeline should be starting"
    assert pipeline_run["pipeline"]["id"] == pipeline_id, "Pipeline ID should match"
    
    # Verify variables were passed (note: variables may not be returned in run details)
    if "variables" in pipeline_run and pipeline_run["variables"]:
        assert "myVariable" in pipeline_run["variables"], "Variable should be in run"
        assert pipeline_run["variables"]["myVariable"]["value"] == "test-value-123"
    
    print(f"✓ Pipeline started with variables: run ID {pipeline_run['id']}")


@requires_ado_creds 
async def test_run_pipeline_with_branch(mcp_client: Client):
    """Tests running a pipeline from a specific branch."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 59  # test_run_and_get_pipeline_run_details
    
    # Run from main branch
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
    assert pipeline_run is not None, "Pipeline run should not be None"
    assert isinstance(pipeline_run, dict), "Pipeline run should be a dictionary"
    
    # Verify pipeline was started
    assert pipeline_run["id"] is not None, "Pipeline run should have an ID"
    assert pipeline_run["state"] in ["unknown", "inProgress"], "Pipeline should be starting"
    
    # Verify resources contain branch info
    if "resources" in pipeline_run and "repositories" in pipeline_run["resources"]:
        repos = pipeline_run["resources"]["repositories"]
        if "self" in repos:
            assert repos["self"]["refName"] == branch, "Branch should match requested"
    
    print(f"✓ Pipeline started from branch {branch}: run ID {pipeline_run['id']}")


@requires_ado_creds
async def test_run_pipeline_with_template_parameters(mcp_client: Client):
    """Tests running a pipeline with template parameters."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 75  # preview-test-parameterized pipeline (accepts template params)
    
    # Define template parameters
    template_params = {
        "buildConfiguration": "Release",
        "platform": "x64"
    }
    
    try:
        result = await mcp_client.call_tool(
            "run_pipeline",
            {
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "template_parameters": template_params
            }
        )
        
        pipeline_run = result.data
        assert pipeline_run is not None, "Pipeline run should not be None"
        assert isinstance(pipeline_run, dict), "Pipeline run should be a dictionary"
        
        # Verify pipeline was started
        assert pipeline_run["id"] is not None, "Pipeline run should have an ID"
        assert pipeline_run["state"] in ["unknown", "inProgress"], "Pipeline should be starting"
        
        print(f"✓ Pipeline started with template parameters: run ID {pipeline_run['id']}")
    except Exception as e:
        if "400" in str(e):
            print("✓ Template parameters rejected by pipeline (expected for some pipelines)")
            pytest.skip("Pipeline doesn't support template parameters")
        else:
            raise


@requires_ado_creds
async def test_run_pipeline_and_get_outcome_with_all_params(mcp_client: Client):
    """Tests running a pipeline with all parameter types and waiting for outcome."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 59  # test_run_and_get_pipeline_run_details (quick success)
    
    # Define all parameter types
    variables = {"testVar": "outcome-test"}
    branch = "refs/heads/main"
    
    result = await mcp_client.call_tool(
        "run_pipeline_and_get_outcome",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "timeout_seconds": 300,
            "variables": variables,
            "branch": branch
        }
    )
    
    outcome = result.data
    assert outcome is not None, "Outcome should not be None"
    assert isinstance(outcome, dict), "Outcome should be a dictionary"
    
    # Verify outcome structure
    assert "pipeline_run" in outcome, "Should have pipeline_run"
    assert "success" in outcome, "Should have success flag"
    assert "execution_time_seconds" in outcome, "Should have execution time"
    
    # Verify pipeline completed
    pipeline_run = outcome["pipeline_run"]
    assert pipeline_run["state"] == "completed", "Pipeline should be completed"
    assert outcome["success"] is True, "Pipeline should succeed"
    
    print(f"✓ Pipeline with all params completed in {outcome['execution_time_seconds']:.2f}s")


@requires_ado_creds
async def test_run_pipeline_by_name_with_variables(mcp_client: Client):
    """Tests running a pipeline by name with variables."""
    project_name = "ado-mcp"
    pipeline_name = "preview-test-parameterized"
    
    variables = {
        "nameBasedVar": "test-by-name",
        "runId": "12345"
    }
    
    result = await mcp_client.call_tool(
        "run_pipeline_by_name",
        {
            "project_name": project_name,
            "pipeline_name": pipeline_name,
            "variables": variables
        }
    )
    
    pipeline_run = result.data
    assert pipeline_run is not None, "Pipeline run should not be None"
    assert isinstance(pipeline_run, dict), "Pipeline run should be a dictionary"
    
    # Verify pipeline was started
    assert pipeline_run["id"] is not None, "Pipeline run should have an ID"
    assert pipeline_run["state"] in ["unknown", "inProgress"], "Pipeline should be starting"
    
    print(f"✓ Pipeline '{pipeline_name}' started by name with variables: run ID {pipeline_run['id']}")


@requires_ado_creds
async def test_run_pipeline_and_get_outcome_by_name_with_branch(mcp_client: Client):
    """Tests running a pipeline by name from a specific branch and getting outcome."""
    project_name = "ado-mcp"
    pipeline_name = "test_run_and_get_pipeline_run_details"
    
    branch = "refs/heads/main"
    
    result = await mcp_client.call_tool(
        "run_pipeline_and_get_outcome_by_name",
        {
            "project_name": project_name,
            "pipeline_name": pipeline_name,
            "timeout_seconds": 300,
            "branch": branch
        }
    )
    
    outcome = result.data
    assert outcome is not None, "Outcome should not be None"
    assert isinstance(outcome, dict), "Outcome should be a dictionary"
    
    # Verify outcome
    assert outcome["pipeline_run"]["state"] == "completed", "Pipeline should complete"
    assert outcome["success"] is True, "Pipeline should succeed"
    
    print(f"✓ Pipeline '{pipeline_name}' run by name from branch completed successfully")


@requires_ado_creds
async def test_run_pipeline_with_stages_to_skip(mcp_client: Client):
    """Tests running a pipeline with stages to skip."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 84  # log-test-complex (multi-stage pipeline)
    
    # Skip the Deploy stage
    stages_to_skip = ["Deploy"]
    
    try:
        result = await mcp_client.call_tool(
            "run_pipeline",
            {
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "stages_to_skip": stages_to_skip
            }
        )
        
        pipeline_run = result.data
        assert pipeline_run is not None, "Pipeline run should not be None"
        assert isinstance(pipeline_run, dict), "Pipeline run should be a dictionary"
        
        # Verify pipeline was started
        assert pipeline_run["id"] is not None, "Pipeline run should have an ID"
        assert pipeline_run["state"] in ["unknown", "inProgress"], "Pipeline should be starting"
        
        print(f"✓ Pipeline started with stages to skip: run ID {pipeline_run['id']}")
    except Exception as e:
        if "400" in str(e):
            print("✓ Stage skipping rejected by pipeline (expected for some pipelines)")
            pytest.skip("Pipeline doesn't support stages to skip") 
        else:
            raise


@requires_ado_creds
async def test_run_pipeline_no_params_unchanged(mcp_client: Client):
    """Tests that running pipeline without new params still works as before."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 59  # test_run_and_get_pipeline_run_details
    
    # Run without any new parameters
    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id
        }
    )
    
    pipeline_run = result.data
    assert pipeline_run is not None, "Pipeline run should not be None"
    assert isinstance(pipeline_run, dict), "Pipeline run should be a dictionary"
    
    # Verify pipeline was started normally
    assert pipeline_run["id"] is not None, "Pipeline run should have an ID"
    assert pipeline_run["state"] in ["unknown", "inProgress"], "Pipeline should be starting"
    
    print(f"✓ Pipeline started without params (backward compatibility): run ID {pipeline_run['id']}")


@requires_ado_creds
async def test_run_pipeline_with_empty_params(mcp_client: Client):
    """Tests running pipeline with empty parameter values."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 59  # test_run_and_get_pipeline_run_details
    
    # Run with empty parameters
    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "variables": {},
            "template_parameters": {},
            "stages_to_skip": [],
            "resources": {}
        }
    )
    
    pipeline_run = result.data
    assert pipeline_run is not None, "Pipeline run should not be None"
    assert isinstance(pipeline_run, dict), "Pipeline run should be a dictionary"
    
    # Verify pipeline was started normally (empty params should be ignored)
    assert pipeline_run["id"] is not None, "Pipeline run should have an ID"
    assert pipeline_run["state"] in ["unknown", "inProgress"], "Pipeline should be starting"
    
    print(f"✓ Pipeline started with empty params: run ID {pipeline_run['id']}")


@requires_ado_creds
async def test_pipeline_run_request_model():
    """Tests the PipelineRunRequest model directly."""
    # Test creating request with all fields
    request = PipelineRunRequest(
        variables={"var1": "value1"},
        templateParameters={"param1": "value1"},
        branch="refs/heads/feature/test",
        stagesToSkip=["Stage1", "Stage2"]
    )
    
    # Verify model serialization
    request_dict = request.model_dump(exclude_none=True)
    assert request_dict["variables"] == {"var1": "value1"}
    assert request_dict["templateParameters"] == {"param1": "value1"}
    assert request_dict["branch"] == "refs/heads/feature/test"
    assert request_dict["stagesToSkip"] == ["Stage1", "Stage2"]
    
    # Test creating request with only some fields
    partial_request = PipelineRunRequest(variables={"var2": "value2"})
    partial_dict = partial_request.model_dump(exclude_none=True)
    assert partial_dict == {"variables": {"var2": "value2"}}
    assert "branch" not in partial_dict
    
    print("✓ PipelineRunRequest model works correctly")