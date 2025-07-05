import unittest
import asyncio
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_FILE_PATH = "server.py"


class TestServerEndToEndBase(unittest.IsolatedAsyncioTestCase):
    """
    Base class for end-to-end tests for the MCP server's tools.
    """

    def setUp(self):
        self.server_params = StdioServerParameters(
            command="python3",
            args=[SERVER_FILE_PATH],
            env=os.environ
        )
        if not all([os.environ.get("ADO_ORGANIZATION_URL"), os.environ.get("AZURE_DEVOPS_EXT_PAT")]):
            self.fail("Required environment variables for end-to-end tests are not set. "
                      "Please set ADO_ORGANIZATION_URL and AZURE_DEVOPS_EXT_PAT.")

    async def test_list_tools_exposes_tools_correctly(self):
        """
        Verifies that the server correctly lists the 'pipelines/list' and 'pipelines/get' tools
        with the expected schema.
        """
        async with stdio_client(self.server_params) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                response = await session.list_tools()

                self.assertIsNotNone(response.tools)
                self.assertEqual(len(response.tools), 3)

                # Test pipelines/list tool
                list_tool = next((t for t in response.tools if t.name == "pipelines/list"), None)
                self.assertIsNotNone(list_tool)
                self.assertEqual(list_tool.description, "Lists all pipelines in a given Azure DevOps project.")
                list_params = list_tool.inputSchema
                self.assertEqual(list_params["type"], "object")
                self.assertIn("project_name", list_params["properties"])
                self.assertEqual(list_params["properties"]["project_name"]["type"], "string")
                self.assertIn("project_name", list_params["required"])

                # Test pipelines/get tool
                get_tool = next((t for t in response.tools if t.name == "pipelines/get"), None)
                self.assertIsNotNone(get_tool)
                self.assertEqual(get_tool.description, "Gets the detailed definition of a single pipeline, including its parameters.")
                get_params = get_tool.inputSchema
                self.assertEqual(get_params["type"], "object")
                self.assertIn("project_name", get_params["properties"])
                self.assertEqual(get_params["properties"]["project_name"]["type"], "string")
                self.assertIn("pipeline_id", get_params["properties"])
                self.assertEqual(get_params["properties"]["pipeline_id"]["type"], "integer")
                self.assertIn("project_name", get_params["required"])
                self.assertIn("pipeline_id", get_params["required"])

                # Test builds/get tool
                get_build_tool = next((t for t in response.tools if t.name == "builds/get"), None)
                self.assertIsNotNone(get_build_tool)
                self.assertEqual(get_build_tool.description, "Gets the detailed definition of a single build definition, including its parameters.")
                get_build_params = get_build_tool.inputSchema
                self.assertEqual(get_build_params["type"], "object")
                self.assertIn("project_name", get_build_params["properties"])
                self.assertEqual(get_build_params["properties"]["project_name"]["type"], "string")
                self.assertIn("definition_id", get_build_params["properties"])
                self.assertEqual(get_build_params["properties"]["definition_id"]["type"], "integer")
                self.assertIn("project_name", get_build_params["required"])
                self.assertIn("definition_id", get_build_params["required"])


class TestListPipelinesEndToEnd(TestServerEndToEndBase):
    """
    End-to-end tests for the 'pipelines/list' tool.
    """

    def setUp(self):
        super().setUp()
        self.project_name = os.environ.get("ADO_PROJECT_NAME")
        if not self.project_name:
            self.fail("Required environment variable ADO_PROJECT_NAME is not set.")

    async def test_list_pipelines_tool(self):
        """
        Verifies that the 'pipelines/list' tool returns a list of pipelines.
        """
        async with stdio_client(self.server_params) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()

                response = await session.call_tool(
                    "pipelines/list",
                    arguments={"project_name": self.project_name}
                )

                self.assertIsNotNone(response.structuredContent)
                self.assertIsInstance(response.structuredContent, list)
                if len(response.structuredContent) > 0:
                    pipeline = response.structuredContent[0]
                    self.assertIn("id", pipeline)
                    self.assertIn("name", pipeline)
                    self.assertIsInstance(pipeline["id"], int)
                    self.assertIsInstance(pipeline["name"], str)


class TestGetPipelineDetailsEndToEnd(TestServerEndToEndBase):
    """
    End-to-end tests for the 'pipelines/get' tool.
    """

    def setUp(self):
        super().setUp()
        self.project_name = os.environ.get("ADO_PROJECT_NAME")
        self.pipeline_id = os.environ.get("ADO_PIPELINE_ID")
        if not all([self.project_name, self.pipeline_id]):
            self.fail("Required environment variables ADO_PROJECT_NAME and ADO_PIPELINE_ID are not set.")

    async def test_get_pipeline_details_tool(self):
        """
        Verifies that the 'pipelines/get' tool returns pipeline details.
        """
        async with stdio_client(self.server_params) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()

                response = await session.call_tool(
                    "pipelines/get",
                    arguments={
                        "project_name": self.project_name,
                        "pipeline_id": int(self.pipeline_id)
                    }
                )
                pipeline_details = response.structuredContent
                self.assertIsNotNone(pipeline_details)
                self.assertIsInstance(pipeline_details, dict)
                self.assertEqual(pipeline_details["id"], int(self.pipeline_id))
                self.assertIn("name", pipeline_details)
                self.assertIn("parameters", pipeline_details)
                self.assertIsInstance(pipeline_details["parameters"], list)


class TestGetBuildDefinitionEndToEnd(TestServerEndToEndBase):
    """
    End-to-end tests for the 'builds/get' tool.
    """

    def setUp(self):
        super().setUp()
        self.project_name = os.environ.get("ADO_PROJECT_NAME")
        self.definition_id = os.environ.get("ADO_PIPELINE_ID")
        if not all([self.project_name, self.definition_id]):
            self.fail("Required environment variables ADO_PROJECT_NAME and ADO_PIPELINE_ID are not set.")

    async def test_get_build_definition_tool(self):
        """
        Verifies that the 'builds/get' tool returns build definition details.
        """
        async with stdio_client(self.server_params) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()

                response = await session.call_tool(
                    "builds/get",
                    arguments={
                        "project_name": self.project_name,
                        "definition_id": int(self.definition_id)
                    }
                )
                build_definition = response.structuredContent
                self.assertIsNotNone(build_definition)
                self.assertIsInstance(build_definition, dict)
                self.assertEqual(build_definition["id"], int(self.definition_id))
                self.assertIn("name", build_definition)


if __name__ == '__main__':
    unittest.main()
