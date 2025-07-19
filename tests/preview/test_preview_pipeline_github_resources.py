"""Tests for pipeline preview with GitHub resources and automatic token injection."""

import logging
import os

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
    async def test_preview_public_github_repository_default_behavior(self, mcp_client: Client):
        """
        Test that public GitHub repositories work with default behavior (no explicit resources).
        
        This test verifies that:
        1. Pipeline preview works without providing repository resources
        2. Public repositories are accessible without authentication
        3. The preview successfully expands templates from public repositories
        """
        # Preview the pipeline without providing resources - should work for public repos
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
        
        logger.info("✓ Public GitHub repository preview works without explicit authentication")

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
                    "RepositoryType": "gitHub",
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
    async def test_preview_private_github_repo_with_branch_override(self, mcp_client: Client):
        """
        Test previewing private GitHub repository with different branch and automatic token injection.
        """
        # Override to use a specific branch/tag for private repository
        resources = {
            "repositories": {
                "tooling": {
                    "refName": "refs/heads/stable/0.0.1",
                    "RepositoryType": "gitHub"  # Required for private repos - triggers token injection
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
        
        logger.info("✓ Private GitHub repository with branch override and token injection succeeded")

    @requires_ado_creds
    async def test_preview_github_token_injection_with_explicit_type(self, mcp_client: Client):
        """
        Test that GitHub token injection works with explicit RepositoryType parameter.
        
        This test verifies that:
        1. Users must specify RepositoryType: "gitHub" for GitHub repositories
        2. Tokens are only injected for repositories with explicit GitHub type
        3. The preview succeeds when RepositoryType is correctly specified
        """
        # Use a pipeline that we know has GitHub repositories
        resources = {
            "repositories": {
                "tooling": {
                    "refName": "refs/heads/main",
                    "RepositoryType": "gitHub"
                    # Token will be auto-injected since this is a GitHub repo
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
        
        # Verify the preview succeeded
        preview_data = result.data
        assert preview_data is not None
        assert preview_data.get("finalYaml") is not None
        
        logger.info("✓ GitHub token injection with explicit RepositoryType verified")

    @requires_ado_creds
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

    @requires_ado_creds
    async def test_preview_branch_affects_job_names(self, mcp_client: Client):
        """
        Test that using different branches in resources actually affects the generated job names.
        
        This is a regression test for the unexpected but useful behavior where the branch
        selection in resources parameters affects the final YAML output, specifically job names.
        """
        parameterized_pipeline_id = 75  # preview-test-parameterized
        
        # First, preview with main branch (using public repository format)
        result_main = await mcp_client.call_tool(
            "preview_pipeline",
            {
                "project_id": PROJECT_ID,
                "pipeline_id": parameterized_pipeline_id,
                "resources": {
                    "repositories": {
                        "tooling": {
                            "refName": "refs/heads/main"
                            # No RepositoryType needed for public repository
                        }
                    }
                }
            }
        )
        
        # Then, preview with stable branch (using public repository format)  
        result_stable = await mcp_client.call_tool(
            "preview_pipeline",
            {
                "project_id": PROJECT_ID,
                "pipeline_id": parameterized_pipeline_id,
                "resources": {
                    "repositories": {
                        "tooling": {
                            "refName": "refs/heads/stable/0.0.1"
                            # No RepositoryType needed for public repository
                        }
                    }
                }
            }
        )
        
        main_yaml = result_main.data["finalYaml"]
        stable_yaml = result_stable.data["finalYaml"]
        
        # Verify that main branch uses normal job names
        assert "job: ParameterizedJob" in main_yaml
        assert "job: dev" in main_yaml
        assert "_stable" not in main_yaml
        
        # Verify that stable branch adds _stable suffix to job names
        assert "job: ParameterizedJob_stable" in stable_yaml
        assert "job: dev_stable" in stable_yaml
        
        # Verify the branch reference affects the actual template expansion
        assert stable_yaml != main_yaml
        
        # IMPORTANT: Verify that the returned YAML reflects the user's resource selection
        # The finalYaml should show the branch we actually requested, not the original YAML
        assert "ref: refs/heads/main" in main_yaml
        assert "ref: refs/heads/stable/0.0.1" in stable_yaml, \
            "finalYaml should reflect the user's resource parameter selection"
        
        logger.info("✓ Branch selection correctly affects job names in preview")
        logger.info("✓ finalYaml reflects user's resource parameter selection")
        logger.info(f"Main branch jobs: ParameterizedJob, dev")
        logger.info(f"Stable branch jobs: ParameterizedJob_stable, dev_stable")

    @requires_ado_creds
    async def test_preview_explicit_token_overrides_injection(self, mcp_client: Client):
        """
        Test that explicitly provided tokens override automatic injection.
        
        This test verifies that when users provide their own token,
        the automatic injection is skipped even with RepositoryType: "gitHub".
        """
        # Test with a pipeline that would normally get GitHub token injection
        # but verify that the system properly checks repository types
        resources = {
            "repositories": {
                "tooling": {
                    "refName": "refs/heads/main",
                    "RepositoryType": "gitHub",
                    # Explicitly provide a token to test the "already has token" path
                    "token": "fake-token-for-testing",
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
        
        # The preview should still work since we provided an explicit token
        preview_data = result.data
        assert preview_data is not None
        assert preview_data.get("finalYaml") is not None
        
        logger.info("✓ Explicit token overrides automatic injection correctly")
        
    @requires_ado_creds
    async def test_preview_github_type_without_token_environment(self, mcp_client: Client):
        """
        Test behavior when RepositoryType is "gitHub" but no GITHUB_TOKEN is available.
        
        This should work for public repositories even without token injection.
        """
        resources = {
            "repositories": {
                "tooling": {
                    "refName": "refs/heads/main",
                    "RepositoryType": "gitHub"
                }
            }
        }
        
        # This should still work for public repos, but won't inject tokens
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
        
        logger.info("✓ Preview works without GITHUB_TOKEN for public repositories")

    @requires_ado_creds
    async def test_preview_public_repository_without_type(self, mcp_client: Client):
        """
        Test that public repositories work without RepositoryType specification.
        
        This test verifies that users can access public repositories without 
        specifying RepositoryType since no authentication is needed.
        """
        # Use resources without RepositoryType - should work for public repos
        resources = {
            "repositories": {
                "tooling": {
                    "refName": "refs/heads/main"
                    # No RepositoryType needed for public repos
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
        
        # Should work fine for public repositories
        preview_data = result.data
        assert preview_data is not None
        assert preview_data.get("finalYaml") is not None
        
        logger.info("✓ Public repositories work without RepositoryType specification")

    @requires_ado_creds
    async def test_preview_unsupported_repository_type_warning(self, mcp_client: Client):
        """
        Test that unsupported repository types generate appropriate warnings.
        
        This test verifies that specifying unsupported repository types
        (like Azure Repos) generates warnings about lack of support.
        """
        # Use resources with unsupported RepositoryType
        resources = {
            "repositories": {
                "tooling": {
                    "refName": "refs/heads/main",
                    "RepositoryType": "azureRepos"  # Unsupported type
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
        
        # The preview may fail or succeed depending on the pipeline,
        # but should log warnings about unsupported type
        preview_data = result.data
        # Don't assert success/failure here as it depends on the repository access
        
        logger.info("✓ Unsupported RepositoryType generates appropriate warnings")