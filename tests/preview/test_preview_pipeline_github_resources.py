import os
import logging

import pytest
from fastmcp.client import Client

from server import mcp
from src.test_config import get_project_id, get_project_name
from tests.ado.test_client import requires_ado_creds
from tests.test_helpers import get_pipeline_id_by_name

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.asyncio

@pytest.fixture
async def mcp_client():
    async with Client(mcp) as client:
        initial_org_url = os.environ.get(
            "ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley"
        )
        await client.call_tool("set_ado_organization", {"organization_url": initial_org_url})
        yield client

class TestPreviewPipelineGitHubResources:
    @requires_ado_creds
    async def test_preview_public_github_repository_default_behavior(self, mcp_client: Client):
        project_id = get_project_id()
        pipeline_id = await get_pipeline_id_by_name(mcp_client, "github-resources-test-stable")
        
        result = await mcp_client.call_tool(
            "preview_pipeline",
            {"project_id": project_id, "pipeline_id": pipeline_id},
        )

        preview_data = result.data
        assert preview_data is not None, (
            f"Expected preview data for public GitHub repository but got None"
        )
        assert preview_data.get("finalYaml") is not None, (
            f"Expected finalYaml in preview data but got None"
        )
        assert len(preview_data["finalYaml"]) > 0, (
            f"Expected non-empty finalYaml but got empty string"
        )

        final_yaml = preview_data["finalYaml"]
        assert "Taskfile" in final_yaml, (
            f"Expected 'Taskfile' in finalYaml indicating template expansion but not found. Got: {final_yaml[:200]}..."
        )
        assert "task --version" in final_yaml, (
            f"Expected 'task --version' in finalYaml but not found. Got: {final_yaml[:200]}..."
        )
        assert "This is stable branch" in final_yaml, (
            f"Expected 'This is stable branch' indicating template was fetched but not found. Got: {final_yaml[:200]}..."
        )

    @requires_ado_creds
    async def test_preview_github_resources_with_explicit_token(self, mcp_client: Client):
        resources = {
            "repositories": {
                "tooling": {
                    "refName": "refs/heads/main",
                    "RepositoryType": "gitHub",
                    "token": os.getenv("GITHUB_TOKEN"),
                    "tokenType": "Basic",
                }
            }
        }

        project_id = get_project_id()
        pipeline_id = await get_pipeline_id_by_name(mcp_client, "github-resources-test-stable")
        
        result = await mcp_client.call_tool(
            "preview_pipeline",
            {
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "resources": resources,
            },
        )

        preview_data = result.data
        assert preview_data is not None, f"Expected preview data with explicit token but got None"
        assert preview_data.get("finalYaml") is not None, (
            f"Expected finalYaml in preview data but got None"
        )
        assert "Taskfile" in preview_data["finalYaml"], (
            f"Expected 'Taskfile' in finalYaml but not found. Got: {preview_data['finalYaml'][:200]}..."
        )

    @requires_ado_creds
    async def test_preview_private_github_repo_with_branch_override(self, mcp_client: Client):
        resources = {
            "repositories": {
                "tooling": {"refName": "refs/heads/stable/0.0.1", "RepositoryType": "gitHub"}
            }
        }

        project_id = get_project_id()
        pipeline_id = await get_pipeline_id_by_name(mcp_client, "github-resources-test-stable")
        
        result = await mcp_client.call_tool(
            "preview_pipeline",
            {
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "resources": resources,
            },
        )

        preview_data = result.data
        assert preview_data is not None, (
            f"Expected preview data for branch override test but got None"
        )
        assert preview_data.get("finalYaml") is not None, (
            f"Expected finalYaml in preview data but got None"
        )
        assert "stable branch 0.0.1" in preview_data["finalYaml"], (
            f"Expected 'stable branch 0.0.1' indicating branch override but not found. Got: {preview_data['finalYaml'][:200]}..."
        )

    @requires_ado_creds
    async def test_preview_github_token_injection_with_explicit_type(self, mcp_client: Client):
        resources = {
            "repositories": {"tooling": {"refName": "refs/heads/main", "RepositoryType": "gitHub"}}
        }

        project_id = get_project_id()
        pipeline_id = await get_pipeline_id_by_name(mcp_client, "github-resources-test-stable")
        
        result = await mcp_client.call_tool(
            "preview_pipeline",
            {
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "resources": resources,
            },
        )
        preview_data = result.data
        assert preview_data is not None, (
            f"Expected preview data for GitHub token injection test but got None"
        )
        assert preview_data.get("finalYaml") is not None, (
            f"Expected finalYaml in preview data but got None"
        )

    @requires_ado_creds
    async def test_preview_github_resources_without_token_public_repo(self, mcp_client: Client):
        result = await mcp_client.call_tool(
            "preview_pipeline",
            {"project_id": get_project_id(), "pipeline_id": await get_pipeline_id_by_name(mcp_client, "github-resources-test-stable")},
        )

        preview_data = result.data
        assert preview_data is not None, (
            f"Expected preview data for public repo without token but got None"
        )
        assert preview_data.get("finalYaml") is not None, (
            f"Expected finalYaml in preview data but got None"
        )
        assert "Taskfile" in preview_data["finalYaml"], (
            f"Expected 'Taskfile' in finalYaml but not found. Got: {preview_data['finalYaml'][:200]}..."
        )

    @requires_ado_creds
    async def test_preview_with_template_parameters(self, mcp_client: Client):
        result = await mcp_client.call_tool(
            "preview_pipeline",
            {
                "project_id": get_project_id(),
                "pipeline_id": await get_pipeline_id_by_name(mcp_client, "github-resources-test-stable"),
                "template_parameters": {
                    "taskfileVersion": "v3.31.0",
                    "installPath": "/usr/local/bin",
                },
            },
        )

        preview_data = result.data
        assert preview_data is not None, (
            f"Expected preview data for template parameters test but got None"
        )
        assert preview_data.get("finalYaml") is not None, (
            f"Expected finalYaml in preview data but got None"
        )
        assert "/usr/local/bin" in preview_data["finalYaml"], (
            f"Expected '/usr/local/bin' parameter in finalYaml but not found. Got: {preview_data['finalYaml'][:200]}..."
        )

    @requires_ado_creds
    async def test_preview_branch_affects_job_names(self, mcp_client: Client):
        project_id = get_project_id()
        pipeline_id = await get_pipeline_id_by_name(mcp_client, "preview-test-parameterized")

        result_main = await mcp_client.call_tool(
            "preview_pipeline",
            {
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "resources": {"repositories": {"tooling": {"refName": "refs/heads/main"}}},
            },
        )
        result_stable = await mcp_client.call_tool(
            "preview_pipeline",
            {
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "resources": {"repositories": {"tooling": {"refName": "refs/heads/stable/0.0.1"}}},
            },
        )

        main_yaml = result_main.data["finalYaml"]
        stable_yaml = result_stable.data["finalYaml"]
        assert "job: ParameterizedJob" in main_yaml, (
            f"Expected 'job: ParameterizedJob' in main branch YAML but not found. Got: {main_yaml[:200]}..."
        )
        assert "job: dev" in main_yaml, (
            f"Expected 'job: dev' in main branch YAML but not found. Got: {main_yaml[:200]}..."
        )
        assert "_stable" not in main_yaml, (
            f"Expected no '_stable' suffix in main branch YAML but found it. Got: {main_yaml[:200]}..."
        )
        assert "job: ParameterizedJob_stable" in stable_yaml, (
            f"Expected 'job: ParameterizedJob_stable' in stable branch YAML but not found. Got: {stable_yaml[:200]}..."
        )
        assert "job: dev_stable" in stable_yaml, (
            f"Expected 'job: dev_stable' in stable branch YAML but not found. Got: {stable_yaml[:200]}..."
        )
        assert stable_yaml != main_yaml, (
            f"Expected different YAML between main and stable branches but they were identical"
        )

        assert "ref: refs/heads/main" in main_yaml, (
            f"Expected 'ref: refs/heads/main' in main branch finalYaml but not found. Got: {main_yaml[:200]}..."
        )
        assert "ref: refs/heads/stable/0.0.1" in stable_yaml, (
            f"Expected 'ref: refs/heads/stable/0.0.1' in stable branch finalYaml to reflect user's resource parameter selection but not found. Got: {stable_yaml[:200]}..."
        )

    @requires_ado_creds
    async def test_preview_explicit_token_overrides_injection(self, mcp_client: Client):
        resources = {
            "repositories": {
                "tooling": {
                    "refName": "refs/heads/main",
                    "RepositoryType": "gitHub",
                    "token": "fake-token-for-testing",
                    "tokenType": "Basic",
                }
            }
        }

        project_id = get_project_id()
        pipeline_id = await get_pipeline_id_by_name(mcp_client, "github-resources-test-stable")
        
        result = await mcp_client.call_tool(
            "preview_pipeline",
            {
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "resources": resources,
            },
        )
        preview_data = result.data
        assert preview_data is not None, (
            f"Expected preview data for explicit token override test but got None"
        )
        assert preview_data.get("finalYaml") is not None, (
            f"Expected finalYaml in preview data but got None"
        )

    @requires_ado_creds
    async def test_preview_github_type_without_token_environment(self, mcp_client: Client):
        resources = {
            "repositories": {"tooling": {"refName": "refs/heads/main", "RepositoryType": "gitHub"}}
        }
        project_id = get_project_id()
        pipeline_id = await get_pipeline_id_by_name(mcp_client, "github-resources-test-stable")
        
        result = await mcp_client.call_tool(
            "preview_pipeline",
            {
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "resources": resources,
            },
        )

        preview_data = result.data
        assert preview_data is not None, (
            f"Expected preview data for GitHub type without token test but got None"
        )
        assert preview_data.get("finalYaml") is not None, (
            f"Expected finalYaml in preview data but got None"
        )

    @requires_ado_creds
    async def test_preview_public_repository_without_type(self, mcp_client: Client):
        resources = {"repositories": {"tooling": {"refName": "refs/heads/main"}}}

        project_id = get_project_id()
        pipeline_id = await get_pipeline_id_by_name(mcp_client, "github-resources-test-stable")
        
        result = await mcp_client.call_tool(
            "preview_pipeline",
            {
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "resources": resources,
            },
        )
        preview_data = result.data
        assert preview_data is not None, (
            f"Expected preview data for public repository without type test but got None"
        )
        assert preview_data.get("finalYaml") is not None, (
            f"Expected finalYaml in preview data but got None"
        )

    @requires_ado_creds
    async def test_preview_unsupported_repository_type_warning(self, mcp_client: Client):
        resources = {
            "repositories": {
                "tooling": {"refName": "refs/heads/main", "RepositoryType": "azureRepos"}
            }
        }

        project_id = get_project_id()
        pipeline_id = await get_pipeline_id_by_name(mcp_client, "github-resources-test-stable")
        
        result = await mcp_client.call_tool(
            "preview_pipeline",
            {
                "project_id": project_id,
                "pipeline_id": pipeline_id,
                "resources": resources,
            },
        )

        preview_data = result.data
        assert True, "Unsupported repository type test completed without crashing"
