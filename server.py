import os
from mcp.server.fastmcp import FastMCP
from ado_integrations.client import AdoClient

mcp = FastMCP("AdoMcpServer")

# Initialize AdoClient
organization_url = os.environ.get("ADO_ORGANIZATION_URL")
if not organization_url:
    raise ValueError("ADO_ORGANIZATION_URL environment variable not set.")
ado_client = AdoClient(organization_url)

@mcp.tool(
    name="pipelines/list",
    description="Lists all pipelines in a given Azure DevOps project."
)
def list_pipelines(project_name: str) -> list[dict]:
    pipelines = ado_client.list_pipelines(project_name)
    return [p.model_dump() for p in pipelines]

@mcp.tool(
    name="pipelines/get",
    description="Gets the detailed definition of a single pipeline, including its parameters."
)
def get_pipeline_details(project_name: str, pipeline_id: int) -> dict:
    pipeline_definition = ado_client.get_pipeline(project_name, pipeline_id)
    return pipeline_definition.model_dump()

@mcp.tool(
    name="builds/get",
    description="Gets the detailed definition of a single build definition, including its parameters."
)
def get_build_definition(project_name: str, definition_id: int) -> dict:
    build_definition = ado_client.get_build_definition(project_name, definition_id)
    return build_definition.model_dump()

if __name__ == "__main__":
    print("running on port: 6277")
    mcp.run()
