#!/usr/bin/env python3
"""
Test dynamic repository resources override functionality
"""
import asyncio
import time
from fastmcp.client import Client
from server import mcp
import os

async def test_dynamic_repository_resources():
    """Test dynamic repository resources to override YAML-defined branches"""
    
    async with Client(mcp) as client:
        # Set the organization
        org_url = os.environ.get("ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley")
        await client.call_tool("set_ado_organization", {"organization_url": org_url})
        
        project_id = "49e895da-15c6-4211-97df-65c547a59c22"
        pipeline_id = 200  # github-resources-test-stable
        
        print("=== Testing Dynamic Repository Resources Override ===")
        print("This test verifies that the resources parameter can override YAML-defined repository branches")
        print()
        
        # Test 1: Use the default branch (main) from YAML
        print("Test 1: Using default branch from YAML (main)")
        try:
            result = await client.call_tool("run_pipeline", {
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "template_parameters": {
                    "taskfileVersion": "latest",
                    "installPath": "./bin/default"
                },
                "variables": {
                    "testVariable": "default-branch-test"
                }
            })
            
            pipeline_run = result.data
            print(f"✓ Pipeline started: Run ID {pipeline_run['id']}")
            print(f"  Default resources will be used from YAML (tooling@main)")
            
            # Wait for completion to see the resources used
            await wait_for_completion(client, project_id, pipeline_id, pipeline_run['id'])
            
        except Exception as e:
            print(f"✗ Default branch test failed: {e}")
        
        print()
        
        # Test 2: Override with stable/0.0.1 branch using resources parameter
        print("Test 2: Overriding tooling repository to use stable/0.0.1 branch")
        
        # This should override the tooling repository branch from main to stable/0.0.1
        resources = {
            "repositories": {
                "tooling": {
                    "refName": "refs/heads/stable/0.0.1"
                }
            }
        }
        
        try:
            result = await client.call_tool("run_pipeline", {
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "resources": resources,
                "template_parameters": {
                    "taskfileVersion": "latest",
                    "installPath": "./bin/stable"
                },
                "variables": {
                    "testVariable": "stable-branch-override-test"
                }
            })
            
            pipeline_run = result.data
            print(f"✓ Pipeline started with resources override: Run ID {pipeline_run['id']}")
            print(f"  Resources sent: {resources}")
            
            # Check if resources were accepted in the response
            if "resources" in pipeline_run and pipeline_run["resources"]:
                print(f"  Resources in response: {pipeline_run['resources']}")
                
                # Look for the tooling repository in the response
                if "repositories" in pipeline_run["resources"]:
                    repos = pipeline_run["resources"]["repositories"]
                    if "tooling" in repos:
                        tooling_ref = repos["tooling"].get("refName", "not specified")
                        print(f"  Tooling repository refName: {tooling_ref}")
                        
                        if "stable/0.0.1" in tooling_ref:
                            print("  ✅ SUCCESS: Repository resource override is working!")
                        else:
                            print(f"  ⚠ Repository ref doesn't contain stable/0.0.1: {tooling_ref}")
                    else:
                        print("  ⚠ Tooling repository not found in response")
                else:
                    print("  ⚠ No repositories found in response")
            else:
                print("  ⚠ No resources found in response")
            
            # Wait for completion to see the actual resources used
            await wait_for_completion(client, project_id, pipeline_id, pipeline_run['id'])
            
        except Exception as e:
            print(f"✗ Resources override test failed: {e}")
        
        print()
        
        # Test 3: Test with a different branch/tag
        print("Test 3: Testing with a different branch override")
        
        resources_main = {
            "repositories": {
                "tooling": {
                    "refName": "refs/heads/main"
                }
            }
        }
        
        try:
            result = await client.call_tool("run_pipeline", {
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "resources": resources_main,
                "template_parameters": {
                    "taskfileVersion": "latest",
                    "installPath": "./bin/main-override"
                },
                "variables": {
                    "testVariable": "main-branch-override-test"
                }
            })
            
            pipeline_run = result.data
            print(f"✓ Pipeline started with main branch override: Run ID {pipeline_run['id']}")
            print(f"  This should explicitly use main branch even though it's the default")
            
        except Exception as e:
            print(f"✗ Main branch override test failed: {e}")
        
        print()
        print("=== Dynamic Repository Resources Tests Complete ===")
        print("The key test is whether the resources parameter successfully overrides")
        print("the YAML-defined repository branches, allowing dynamic branch selection.")

async def wait_for_completion(client, project_id, pipeline_id, run_id, timeout=180):
    """Wait for pipeline completion and show final status"""
    start_time = time.time()
    
    print(f"  Waiting for pipeline {run_id} to complete...")
    
    while time.time() - start_time < timeout:
        try:
            result = await client.call_tool("get_pipeline_run", {
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "run_id": run_id
            })
            
            state = result.data.get("state", "unknown")
            if state == "completed":
                result_status = result.data.get("result", "unknown")
                print(f"  ✓ Pipeline completed with result: {result_status}")
                
                # Show final resources used
                if "resources" in result.data and result.data["resources"]:
                    final_resources = result.data["resources"]
                    print(f"  Final resources used: {final_resources}")
                    
                    # Check specifically for tooling repository
                    if "repositories" in final_resources:
                        repos = final_resources["repositories"]
                        if "tooling" in repos:
                            tooling_info = repos["tooling"]
                            print(f"  Tooling repository: {tooling_info}")
                
                return result_status
            elif state in ["cancelling", "cancelled"]:
                print(f"  ✗ Pipeline was cancelled: {state}")
                return "cancelled"
            
            await asyncio.sleep(10)
            
        except Exception as e:
            print(f"  Error checking status: {e}")
            break
    
    print(f"  ⚠ Pipeline did not complete within {timeout} seconds")
    return "timeout"

if __name__ == "__main__":
    asyncio.run(test_dynamic_repository_resources())