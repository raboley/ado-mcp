import asyncio
from fastmcp import Client
from my_mcp_server import mcp

async def test_add_tool():
    async with Client(mcp) as client:
        result = await client.call_tool("add", {"a": 5, "b": 3})
        assert result.data == 8

async def test_get_config_resource():
    async with Client(mcp) as client:
        result = await client.read_resource("resource://config")
        assert result[0].text == '''{
  "version": "1.0",
  "author": "MyTeam"
}'''

async def test_personalized_greeting_resource_template():
    async with Client(mcp) as client:
        result = await client.read_resource("greetings://TestUser")
        assert result[0].text == 'Hello, TestUser! Welcome to the MCP server.'
