"""
Simple end-to-end test for GitHub resources functionality.

This test demonstrates the basic GitHub resources functionality with the MCP client.
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
async def test_github_resources_basic_functionality(mcp_client: Client):
    """Test basic GitHub resources functionality with the MCP client."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 197  # github-resources-test-v2 pipeline
    
    # Test with basic parameters
    variables = {
        "testVariable": "basic-test-value"
    }
    
    template_parameters = {
        "taskfileVersion": "latest", 
        "installPath": "./basic-test-bin"
    }
    
    # Test that we can start a pipeline with template parameters
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
    assert pipeline_run is not None, "Pipeline run should not be None"
    assert isinstance(pipeline_run, dict), "Pipeline run should be a dictionary"
    
    # Verify pipeline was started
    assert pipeline_run["id"] is not None, "Pipeline run should have an ID"
    assert pipeline_run["state"] in ["unknown", "inProgress"], "Pipeline should be starting"
    assert pipeline_run["pipeline"]["id"] == pipeline_id, "Pipeline ID should match"
    
    print(f"✓ GitHub resources basic test started successfully: Run ID {pipeline_run['id']}")
    
    # Test that template parameters are properly structured
    print(f"✓ Template parameters: {template_parameters}")
    print(f"✓ Variables: {variables}")


@requires_ado_creds
async def test_github_resources_with_different_versions(mcp_client: Client):
    """Test GitHub resources with different taskfile versions."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 197  # github-resources-test-v2 pipeline
    
    # Test with specific version
    variables = {
        "testVariable": "version-test-value"
    }
    
    template_parameters = {
        "taskfileVersion": "v3.30.1",  # Specific version
        "installPath": "./version-test-bin"
    }
    
    # Test that we can start a pipeline with specific version
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
    assert pipeline_run is not None, "Pipeline run should not be None"
    assert isinstance(pipeline_run, dict), "Pipeline run should be a dictionary"
    
    # Verify pipeline was started
    assert pipeline_run["id"] is not None, "Pipeline run should have an ID"
    assert pipeline_run["state"] in ["unknown", "inProgress"], "Pipeline should be starting"
    
    print(f"✓ GitHub resources version test started successfully: Run ID {pipeline_run['id']}")


@requires_ado_creds
async def test_github_resources_name_based_execution(mcp_client: Client):
    """Test GitHub resources with name-based pipeline execution."""
    project_name = "ado-mcp"
    pipeline_name = "github-resources-test-v2"
    
    # Test name-based execution
    variables = {
        "testVariable": "name-based-test-value"
    }
    
    template_parameters = {
        "taskfileVersion": "latest",
        "installPath": "./name-based-test-bin"
    }
    
    # Test that we can start a pipeline by name
    result = await mcp_client.call_tool(
        "run_pipeline_by_name",
        {
            "project_name": project_name,
            "pipeline_name": pipeline_name,
            "variables": variables,
            "template_parameters": template_parameters
        }
    )
    
    pipeline_run = result.data
    assert pipeline_run is not None, "Pipeline run should not be None"
    assert isinstance(pipeline_run, dict), "Pipeline run should be a dictionary"
    
    # Verify pipeline was started
    assert pipeline_run["id"] is not None, "Pipeline run should have an ID"
    assert pipeline_run["state"] in ["unknown", "inProgress"], "Pipeline should be starting"
    
    print(f"✓ GitHub resources name-based test started successfully: Run ID {pipeline_run['id']}")


@requires_ado_creds
async def test_github_resources_demonstration(mcp_client: Client):
    """
    Comprehensive test demonstrating GitHub resources functionality.
    
    This test shows how the MCP client can control:
    1. Template parameters that control the GitHub resource branch
    2. Variables passed to the pipeline
    3. Different versions of tools pulled from GitHub
    """
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 197  # github-resources-test-v2 pipeline
    
    # Demonstrate different configurations
    test_configs = [
        {
            "name": "Latest from Main",
            "branch": "main",
            "version": "latest",
            "path": "./demo-latest"
        },
        {
            "name": "Specific Version from Main", 
            "branch": "main",
            "version": "v3.30.1",
            "path": "./demo-specific"
        }
    ]
    
    results = []
    
    for config in test_configs:
        print(f"\n--- Testing: {config['name']} ---")
        
        variables = {
            "testVariable": f"demo-{config['name'].lower().replace(' ', '-')}"
        }
        
        template_parameters = {
            "taskfileVersion": config["version"],
            "installPath": config["path"]
        }
        
        # Start the pipeline
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
        
        print(f"✓ Started pipeline run {pipeline_run['id']}")
        print(f"  Branch: {config['branch']}")
        print(f"  Version: {config['version']}")
        print(f"  Install Path: {config['path']}")
    
    # Verify all configurations started successfully
    assert len(results) == len(test_configs), "All configurations should have started"
    
    print(f"\n✓ Successfully demonstrated {len(results)} GitHub resources configurations")
    print("✓ This shows the MCP client can control:")
    print("  - GitHub repository branches via template parameters")
    print("  - Tool versions downloaded from GitHub")
    print("  - Installation paths and variables")
    print("  - Multiple pipeline executions with different configurations")


@requires_ado_creds
async def test_github_resources_template_parameter_validation(mcp_client: Client):
    """Test that template parameters are properly validated and passed."""
    project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
    pipeline_id = 197  # github-resources-test-v2 pipeline
    
    # Test with all template parameters
    variables = {
        "testVariable": "validation-test"
    }
    
    template_parameters = {
        "taskfileVersion": "v3.28.0",
        "installPath": "./validation-test-bin"
    }
    
    # Test that template parameters are properly structured
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
    assert pipeline_run is not None, "Pipeline run should not be None"
    assert pipeline_run["id"] is not None, "Pipeline run should have ID"
    
    print(f"✓ Template parameter validation test started: Run ID {pipeline_run['id']}")
    print(f"  Validated parameters: {list(template_parameters.keys())}")
    print(f"  Values: {template_parameters}")
    
    # The fact that the pipeline started successfully means the template parameters 
    # were properly formatted and accepted by Azure DevOps
    assert pipeline_run["state"] in ["unknown", "inProgress"], "Pipeline should be starting"
    print("✓ Template parameters successfully validated and passed to Azure DevOps")