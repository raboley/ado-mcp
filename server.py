import os
from fastmcp import FastMCP
from ado.client import AdoClient

mcp = FastMCP(name="ado-mcp")
ado_client = None

print("Attempting to initialize Azure DevOps client...")
try:
    org_url = os.environ.get("ADO_ORGANIZATION_URL")
    if not org_url:
        raise ValueError("ADO_ORGANIZATION_URL environment variable is not set.")

    temp_client = AdoClient(organization_url=org_url)
    temp_client.check_authentication()

    ado_client = temp_client
    print("✅ Azure DevOps client initialized and authenticated successfully.")

except Exception as e:
    # Catch any error during initialization (missing PAT, bad credentials, network issues)
    print(f"⚠️  WARNING: Could not initialize Azure DevOps client. ADO features will be disabled.")
    print(f"   Reason: {e}")


# --- Tools and Resources ---

@mcp.tool
def check_authentication():
    """Verifies authentication by making a simple API call."""
    return ado_client.check_authentication()

@mcp.tool
def add(a: int, b: int) -> int:
    """Adds two integer numbers together."""
    return a + b


@mcp.resource("resource://config")
def get_config() -> dict:
    """Provides the application's configuration."""
    return {"version": "1.0", "author": "MyTeam"}


@mcp.resource("greetings://{name}")
def personalized_greeting(name: str) -> str:
    """Generates a personalized greeting for the given name."""
    return f"Hello, {name}! Welcome to the MCP server."


if __name__ == "__main__":  # pragma: no cover
    mcp.run()
