#!/usr/bin/env python3
"""
Create a pipeline that supports runtime variables for testing
"""

import asyncio
import os

from fastmcp.client import Client

from server import mcp


async def create_runtime_variables_pipeline():
    """Create a pipeline that supports runtime variables"""

    async with Client(mcp) as client:
        # Set the organization
        org_url = os.environ.get("ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley")
        await client.call_tool("set_ado_organization", {"organization_url": org_url})

        project_id = "49e895da-15c6-4211-97df-65c547a59c22"

        # Find the GitHub service connection
        print("Finding GitHub service connection...")
        connections = await client.call_tool("list_service_connections", {"project_id": project_id})
        github_connection = None
        for conn in connections.data:
            if conn.get("type", "").lower() == "github" and conn.get("name") == "raboley":
                github_connection = conn
                break

        if not github_connection:
            raise Exception("GitHub service connection 'raboley' not found")

        print(
            f"Found GitHub service connection: {github_connection['name']} (ID: {github_connection['id']})"
        )

        # Create the pipeline
        print("Creating runtime variables test pipeline...")
        pipeline_name = "runtime-variables-test"
        yaml_path = "tests/ado/fixtures/runtime-variables-test.yml"
        repository_name = "raboley/ado-mcp"
        service_connection_id = github_connection["id"]

        try:
            pipeline = await client.call_tool(
                "create_pipeline",
                {
                    "project_id": project_id,
                    "name": pipeline_name,
                    "yaml_path": yaml_path,
                    "repository_name": repository_name,
                    "service_connection_id": service_connection_id,
                    "configuration_type": "yaml",
                    "repository_type": "gitHub",
                },
            )

            print(f"✓ Successfully created pipeline: {pipeline_name}")
            print(f"  Pipeline ID: {pipeline.data.id}")
            print(f"  Pipeline Name: {pipeline.data.name}")
            print(
                f"  Pipeline URL: https://dev.azure.com/RussellBoley/ado-mcp/_build?definitionId={pipeline.data.id}"
            )
            return pipeline.data

        except Exception as e:
            if "409" in str(e):
                print(f"Pipeline '{pipeline_name}' already exists, looking it up...")
                pipelines = await client.call_tool("list_pipelines", {"project_id": project_id})
                for p in pipelines.data:
                    if p["name"] == pipeline_name:
                        print(f"Found existing pipeline: {pipeline_name} (ID: {p['id']})")
                        print(
                            f"Pipeline URL: https://dev.azure.com/RussellBoley/ado-mcp/_build?definitionId={p['id']}"
                        )
                        return p
                raise Exception(f"Pipeline '{pipeline_name}' exists but couldn't be found")
            else:
                raise


if __name__ == "__main__":
    pipeline = asyncio.run(create_runtime_variables_pipeline())
    print("\nPipeline created successfully!")
    print(f"Pipeline ID: {pipeline.id if hasattr(pipeline, 'id') else pipeline['id']}")
    print(f"Pipeline Name: {pipeline.name if hasattr(pipeline, 'name') else pipeline['name']}")
    print("\nNext steps:")
    print("1. Commit and push the YAML file: tests/ado/fixtures/runtime-variables-test.yml")
    print("2. Update the YAML file to include the pipeline URL comment")
    print("3. Configure runtime variables in Azure DevOps UI (Variables tab)")
