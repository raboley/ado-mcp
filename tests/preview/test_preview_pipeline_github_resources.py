"""Tests for pipeline preview with GitHub resources and automatic token injection."""

import logging
import os
from unittest.mock import patch

import pytest
from fastmcp.client import Client

from server import mcp
from tests.ado.test_client import requires_ado_creds

logger = logging.getLogger(__name__)

# Mark all tests in this module as asyncio
pytestmark = pytest.mark.asyncio

# Test configuration
PROJECT_ID = "49e895da-15c6-4211-97df-65c547a59c22"  # ado-mcp project
GITHUB_RESOURCES_PIPELINE_ID = 200  # github-resources-test-stable


@pytest.fixture
async def mcp_client():
    """Provides a connected MCP client for tests."""
    async with Client(mcp) as client:
        initial_org_url = os.environ.get(
            "ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley"
        )
        await client.call_tool("set_ado_organization", {"organization_url": initial_org_url})
        yield client


class TestPreviewPipelineGitHubResources:
    """Test pipeline preview functionality with GitHub resources."""

    @requires_ado_creds
    async def test_preview_github_resources_pipeline_with_auto_token(self, mcp_client: Client):
        """
        Test that GitHub token is automatically injected when previewing pipelines with GitHub resources.
        
        This test verifies that:
        1. Pipeline preview works without manually providing resources
        2. GitHub token from environment is automatically used
        3. The preview successfully expands templates from external repositories
        """
        # Ensure GITHUB_TOKEN is set
        assert os.getenv("GITHUB_TOKEN"), "GITHUB_TOKEN must be set in environment"
        
        # Preview the pipeline without providing resources - token should be auto-injected
        result = await mcp_client.call_tool(
            "preview_pipeline",
            {
                "project_id": PROJECT_ID,
                "pipeline_id": GITHUB_RESOURCES_PIPELINE_ID
            }
        )
        
        preview_data = result.data
        assert preview_data is not None
        assert preview_data.get("finalYaml") is not None
        assert len(preview_data["finalYaml"]) > 0
        
        # Check that the template was expanded (Taskfile installation script should be present)
        assert "Taskfile" in preview_data["finalYaml"]
        assert "task --version" in preview_data["finalYaml"]
        assert "This is stable branch" in preview_data["finalYaml"]  # Indicates template was fetched
        
        logger.info("✓ GitHub resources pipeline preview succeeded with auto-injected token")

    @requires_ado_creds
    async def test_preview_github_resources_with_explicit_token(self, mcp_client: Client):
        """
        Test that explicitly provided tokens override the auto-injection.
        """
        # Provide explicit resources with a different branch
        resources = {
            "repositories": {
                "tooling": {
                    "refName": "refs/heads/main",
                    "token": os.getenv("GITHUB_TOKEN"),
                    "tokenType": "Basic"
                }
            }
        }
        
        result = await mcp_client.call_tool(
            "preview_pipeline",
            {
                "project_id": PROJECT_ID,
                "pipeline_id": GITHUB_RESOURCES_PIPELINE_ID,
                "resources": resources
            }
        )
        
        preview_data = result.data
        assert preview_data is not None
        assert preview_data.get("finalYaml") is not None
        assert "Taskfile" in preview_data["finalYaml"]
        
        logger.info("✓ Preview with explicit token succeeded")

    @requires_ado_creds
    async def test_preview_github_resources_with_branch_override(self, mcp_client: Client):
        """
        Test previewing with a different branch reference.
        """
        # Override to use a specific branch/tag
        resources = {
            "repositories": {
                "tooling": {
                    "refName": "refs/heads/stable/0.0.1"
                    # Token will be auto-injected since we're not providing it
                }
            }
        }
        
        result = await mcp_client.call_tool(
            "preview_pipeline",
            {
                "project_id": PROJECT_ID,
                "pipeline_id": GITHUB_RESOURCES_PIPELINE_ID,
                "resources": resources
            }
        )
        
        preview_data = result.data
        assert preview_data is not None
        assert preview_data.get("finalYaml") is not None
        # The template from stable/0.0.1 branch should be used
        assert "stable branch 0.0.1" in preview_data["finalYaml"]
        
        logger.info("✓ Preview with branch override succeeded")

    @requires_ado_creds
    @patch.dict(os.environ, {"GITHUB_TOKEN": ""}, clear=False)
    async def test_preview_github_resources_without_token_public_repo(self, mcp_client: Client):
        """
        Test that preview still works without token for public GitHub repos.
        
        Note: The raboley/tooling repo is public, so preview should work even without a token.
        This test verifies that the token injection doesn't break when no token is available.
        """
        # This should still work because the pipeline uses a public GitHub repo
        result = await mcp_client.call_tool(
            "preview_pipeline",
            {
                "project_id": PROJECT_ID,
                "pipeline_id": GITHUB_RESOURCES_PIPELINE_ID
            }
        )
        
        preview_data = result.data
        assert preview_data is not None
        assert preview_data.get("finalYaml") is not None
        
        # The template should still be expanded from the public repo
        assert "Taskfile" in preview_data["finalYaml"]
        
        logger.info("✓ Preview works without token for public GitHub repo")

    @requires_ado_creds
    async def test_preview_with_template_parameters(self, mcp_client: Client):
        """
        Test preview with template parameters for the GitHub resources pipeline.
        """
        # Provide template parameters
        result = await mcp_client.call_tool(
            "preview_pipeline",
            {
                "project_id": PROJECT_ID,
                "pipeline_id": GITHUB_RESOURCES_PIPELINE_ID,
                "template_parameters": {
                    "taskfileVersion": "v3.31.0",
                    "installPath": "/usr/local/bin"
                }
            }
        )
        
        preview_data = result.data
        assert preview_data is not None
        assert preview_data.get("finalYaml") is not None
        
        # Check that parameters were applied
        assert "/usr/local/bin" in preview_data["finalYaml"]
        
        logger.info("✓ Preview with template parameters succeeded")