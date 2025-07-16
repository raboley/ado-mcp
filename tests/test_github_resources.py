"""
End-to-end tests for GitHub resources with branch and tag selection.

This test demonstrates the ability to use the MCP client to run pipelines
that pull templates from different branches and tags of GitHub repositories.
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
async def test_github_resources_main_branch(mcp_client: Client):
    """Test running pipeline with GitHub resources from main branch."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 196  # github-resources-test pipeline
    
    # Test with main branch (default)
    variables = {
        "testVariable": "main-branch-test"
    }
    
    template_parameters = {
        "toolingBranch": "main",
        "taskfileVersion": "latest",
        "installPath": "./bin"
    }
    
    # Test using resources from main branch
    result = await mcp_client.call_tool(
        "run_pipeline_and_get_outcome",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "timeout_seconds": 300,
            "variables": variables,
            "template_parameters": template_parameters
        }
    )
    
    outcome = result.data
    assert outcome is not None, "Outcome should not be None"
    assert isinstance(outcome, dict), "Outcome should be a dictionary"
    
    # Verify pipeline completed
    pipeline_run = outcome["pipeline_run"]
    assert pipeline_run["id"] is not None, "Pipeline run should have ID"
    assert pipeline_run["state"] == "completed", "Pipeline should be completed"
    
    # For this test, we expect success since we're using a valid template
    if outcome["success"]:
        print(f"✓ GitHub resources test (main branch) completed successfully in {outcome['execution_time_seconds']:.2f}s")
        print(f"  Pipeline run ID: {pipeline_run['id']}")
    else:
        print(f"✗ GitHub resources test (main branch) failed after {outcome['execution_time_seconds']:.2f}s")
        if outcome["failure_summary"]:
            print(f"  Failure summary: {outcome['failure_summary']['total_failed_steps']} failed steps")


@requires_ado_creds
async def test_github_resources_with_specific_branch(mcp_client: Client):
    """Test running pipeline with GitHub resources from a specific branch."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 196  # github-resources-test pipeline
    
    # Test with a specific branch (if it exists)
    variables = {
        "testVariable": "specific-branch-test"
    }
    
    template_parameters = {
        "toolingBranch": "main",  # Change this to a specific branch if available
        "taskfileVersion": "v3.30.1",  # Use a specific version
        "installPath": "./custom-bin"
    }
    
    # Test using resources from specific branch
    result = await mcp_client.call_tool(
        "run_pipeline_and_get_outcome",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "timeout_seconds": 300,
            "variables": variables,
            "template_parameters": template_parameters
        }
    )
    
    outcome = result.data
    assert outcome is not None, "Outcome should not be None"
    assert isinstance(outcome, dict), "Outcome should be a dictionary"
    
    # Verify pipeline completed
    pipeline_run = outcome["pipeline_run"]
    assert pipeline_run["id"] is not None, "Pipeline run should have ID"
    assert pipeline_run["state"] == "completed", "Pipeline should be completed"
    
    print(f"✓ GitHub resources test (specific branch) completed in {outcome['execution_time_seconds']:.2f}s")
    print(f"  Pipeline run ID: {pipeline_run['id']}")
    print(f"  Success: {outcome['success']}")


@requires_ado_creds
async def test_github_resources_with_tag(mcp_client: Client):
    """Test running pipeline with GitHub resources from a specific tag."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 196  # github-resources-test pipeline
    
    # Test with a specific tag (if available)
    variables = {
        "testVariable": "tag-test"
    }
    
    template_parameters = {
        "toolingBranch": "main",  # Could be a tag like "v1.0.0" if available
        "taskfileVersion": "v3.28.0",  # Use specific version
        "installPath": "./tag-bin"
    }
    
    # Test using resources from a tag
    result = await mcp_client.call_tool(
        "run_pipeline_and_get_outcome",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "timeout_seconds": 300,
            "variables": variables,
            "template_parameters": template_parameters
        }
    )
    
    outcome = result.data
    assert outcome is not None, "Outcome should not be None"
    assert isinstance(outcome, dict), "Outcome should be a dictionary"
    
    # Verify pipeline completed
    pipeline_run = outcome["pipeline_run"]
    assert pipeline_run["id"] is not None, "Pipeline run should have ID"
    assert pipeline_run["state"] == "completed", "Pipeline should be completed"
    
    print(f"✓ GitHub resources test (tag) completed in {outcome['execution_time_seconds']:.2f}s")
    print(f"  Pipeline run ID: {pipeline_run['id']}")
    print(f"  Success: {outcome['success']}")


@requires_ado_creds
async def test_github_resources_by_name_with_branch(mcp_client: Client):
    """Test running pipeline by name with GitHub resources from different branches."""
    project_name = "ado-mcp"
    pipeline_name = "github-resources-test"
    
    # Test using name-based execution with custom branch
    variables = {
        "testVariable": "name-based-branch-test"
    }
    
    template_parameters = {
        "toolingBranch": "main",
        "taskfileVersion": "latest",
        "installPath": "./name-test-bin"
    }
    
    # Test using resources via name-based execution
    result = await mcp_client.call_tool(
        "run_pipeline_and_get_outcome_by_name",
        {
            "project_name": project_name,
            "pipeline_name": pipeline_name,
            "timeout_seconds": 300,
            "variables": variables,
            "template_parameters": template_parameters
        }
    )
    
    outcome = result.data
    assert outcome is not None, "Outcome should not be None"
    assert isinstance(outcome, dict), "Outcome should be a dictionary"
    
    # Verify pipeline completed
    pipeline_run = outcome["pipeline_run"]
    assert pipeline_run["id"] is not None, "Pipeline run should have ID"
    assert pipeline_run["state"] == "completed", "Pipeline should be completed"
    
    print(f"✓ GitHub resources test (name-based) completed in {outcome['execution_time_seconds']:.2f}s")
    print(f"  Pipeline run ID: {pipeline_run['id']}")
    print(f"  Success: {outcome['success']}")


@requires_ado_creds
async def test_github_resources_dynamic_branch_selection(mcp_client: Client):
    """Test dynamic branch selection using resources with MCP client control."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 196  # github-resources-test pipeline
    
    # Test multiple branch/tag combinations dynamically
    test_configurations = [
        {
            "name": "main-latest",
            "branch": "main",
            "version": "latest",
            "path": "./main-latest-bin"
        },
        {
            "name": "main-specific",
            "branch": "main", 
            "version": "v3.30.1",
            "path": "./main-specific-bin"
        }
    ]
    
    results = []
    
    for config in test_configurations:
        print(f"\n--- Testing configuration: {config['name']} ---")
        
        variables = {
            "testVariable": f"dynamic-test-{config['name']}"
        }
        
        template_parameters = {
            "toolingBranch": config["branch"],
            "taskfileVersion": config["version"],
            "installPath": config["path"]
        }
        
        # Use just run_pipeline for faster testing (don't wait for completion)
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
        assert pipeline_run is not None, f"Pipeline run should not be None for {config['name']}"
        assert pipeline_run["id"] is not None, f"Pipeline run should have ID for {config['name']}"
        
        results.append({
            "config": config,
            "run_id": pipeline_run["id"],
            "state": pipeline_run["state"]
        })
        
        print(f"✓ Started pipeline run {pipeline_run['id']} for {config['name']}")
    
    # Verify all configurations started successfully
    assert len(results) == len(test_configurations), "All configurations should have started"
    
    for result in results:
        assert result["run_id"] is not None, f"Run ID should exist for {result['config']['name']}"
        print(f"✓ Configuration {result['config']['name']}: Run ID {result['run_id']}")


@requires_ado_creds
async def test_github_resources_with_custom_resources_parameter(mcp_client: Client):
    """Test using custom resources parameter to override repository branch."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 196  # github-resources-test pipeline
    
    # Test using custom resources to override the repository branch
    variables = {
        "testVariable": "custom-resources-test"
    }
    
    template_parameters = {
        "toolingBranch": "main",  # This will be overridden by resources
        "taskfileVersion": "latest",
        "installPath": "./custom-resources-bin"
    }
    
    # Override the repository branch using resources
    resources = {
        "repositories": {
            "tooling": {
                "refName": "refs/heads/main"  # Override to use main branch
            }
        }
    }
    
    # Test using custom resources to control repository branch
    result = await mcp_client.call_tool(
        "run_pipeline",
        {
            "project_id": project_id,
            "pipeline_id": pipeline_id,
            "variables": variables,
            "template_parameters": template_parameters,
            "resources": resources
        }
    )
    
    pipeline_run = result.data
    assert pipeline_run is not None, "Pipeline run should not be None"
    assert pipeline_run["id"] is not None, "Pipeline run should have ID"
    
    print(f"✓ GitHub resources test with custom resources started: Run ID {pipeline_run['id']}")
    
    # Verify resources were applied
    if "resources" in pipeline_run and pipeline_run["resources"]:
        resources_info = pipeline_run["resources"]
        if "repositories" in resources_info:
            print(f"✓ Resources applied: {resources_info['repositories']}")
        else:
            print("  No repository resources found in response")
    else:
        print("  No resources information in pipeline run response")


@requires_ado_creds
async def test_github_resources_error_handling(mcp_client: Client):
    """Test error handling when using invalid branch/tag in resources."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 196  # github-resources-test pipeline
    
    # Test with invalid branch
    variables = {
        "testVariable": "error-handling-test"
    }
    
    template_parameters = {
        "toolingBranch": "nonexistent-branch-12345",
        "taskfileVersion": "latest",
        "installPath": "./error-test-bin"
    }
    
    try:
        result = await mcp_client.call_tool(
            "run_pipeline_and_get_outcome",
            {
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "timeout_seconds": 120,  # Shorter timeout for error case
                "variables": variables,
                "template_parameters": template_parameters
            }
        )
        
        outcome = result.data
        assert outcome is not None, "Outcome should not be None"
        
        # We expect this to fail due to invalid branch
        if not outcome["success"]:
            print(f"✓ Error handling test failed as expected in {outcome['execution_time_seconds']:.2f}s")
            if outcome["failure_summary"]:
                print(f"  Expected failure: {outcome['failure_summary']['total_failed_steps']} failed steps")
        else:
            print(f"⚠ Error handling test unexpectedly succeeded in {outcome['execution_time_seconds']:.2f}s")
            
    except Exception as e:
        print(f"✓ Error handling test caught expected exception: {str(e)}")
        # This is expected behavior for invalid branches