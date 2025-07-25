#!/usr/bin/env python3
"""
Script to create the GitHub resources test pipeline using the MCP client
"""

import asyncio
import os

from fastmcp.client import Client

from server import mcp


async def create_github_resources_pipeline():
    """Create the GitHub resources test pipeline in Azure DevOps"""

    async with Client(mcp) as client:
        # Set the organization
        org_url = os.environ.get("ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley")
        await client.call_tool("set_ado_organization", {"organization_url": org_url})

        # Project details
        project_id = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project

        # Find the GitHub service connection
        print("Finding GitHub service connection...")
        connections = await client.call_tool("list_service_connections", {"project_id": project_id})
        github_connection = None
        for conn in connections.data:
            if conn.get("type", "").lower() == "github" and conn.get("name") == "raboley":
                github_connection = conn
                break

        if not github_connection:
            raise Exception(
                f"GitHub service connection 'raboley' not found. Available: {connections.data}"
            )

        print(
            f"Found GitHub service connection: {github_connection['name']} (ID: {github_connection['id']})"
        )

        # Create the pipeline
        print("Creating GitHub resources test pipeline...")
        pipeline_name = "github-resources-test-stable"
        yaml_path = "tests/ado/fixtures/github-resources-test.yml"
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
            return pipeline.data

        except Exception as e:
            if "409" in str(e) or "already exists" in str(e):
                print(f"Pipeline '{pipeline_name}' already exists, looking it up...")
                pipelines = await client.call_tool("list_pipelines", {"project_id": project_id})
                for p in pipelines.data:
                    if p["name"] == pipeline_name:
                        print(f"Found existing pipeline: {pipeline_name} (ID: {p['id']})")
                        return p
                raise Exception(f"Pipeline '{pipeline_name}' exists but couldn't be found")
            else:
                raise


if __name__ == "__main__":
    pipeline = asyncio.run(create_github_resources_pipeline())
    print("\nPipeline created successfully!")
    print(f"Pipeline ID: {pipeline['id']}")
    print(f"Pipeline Name: {pipeline['name']}")
