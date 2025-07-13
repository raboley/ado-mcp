"""Azure DevOps MCP Server package."""

from dotenv import load_dotenv

__version__ = "0.1.0"

# Override any existing environment variables with values from .env
load_dotenv(override=True)
