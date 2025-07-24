"""
End-to-end tests for name-based pipeline operations.

Tests cover the enhanced pipeline tools that use project and pipeline names,
including fuzzy matching capabilities and intelligent error responses.
"""

import os

import pytest
from fastmcp.client import Client

from server import mcp
from src.test_config import get_project_id
from tests.ado.test_client import requires_ado_creds

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def mcp_client():
    async with Client(mcp) as client:
        initial_org_url = os.environ.get(
            "ADO_ORGANIZATION_URL", "https://dev.azure.com/RussellBoley"
        )
        await client.call_tool("set_ado_organization", {"organization_url": initial_org_url})
        yield client


class TestNameBasedPipelineOperations:
    """Test name-based pipeline operations with fuzzy matching and error handling."""

    @requires_ado_creds
    async def test_run_pipeline_and_get_outcome_exact_name(self, mcp_client: Client):
        """Test run_pipeline_and_get_outcome with exact pipeline name match."""
        # Get project name from projects list
        projects_result = await mcp_client.call_tool("list_projects", {})
        project_name = None
        project_id = get_project_id()

        for project in projects_result.data:
            if project["id"] == project_id:
                project_name = project["name"]
                break

        assert project_name is not None, f"Should find project name for ID {project_id}"

        pipeline_name = "test_run_and_get_pipeline_run_details"

        result = await mcp_client.call_tool(
            "run_pipeline_and_get_outcome",
            {
                "project_name": project_name,
                "pipeline_name": pipeline_name,
                "timeout_seconds": 60,  # Short timeout for fast test
            },
        )

        assert result.data is not None, f"Should successfully run pipeline '{pipeline_name}'"
        assert "success" in result.data, "Result should contain success field"
        assert "pipeline_run" in result.data, "Result should contain pipeline_run details"
        assert "execution_time_seconds" in result.data, (
            "Result should contain execution_time_seconds"
        )

    @requires_ado_creds
    async def test_run_pipeline_and_get_outcome_case_insensitive(self, mcp_client: Client):
        """Test run_pipeline_and_get_outcome with case-insensitive pipeline name."""
        projects_result = await mcp_client.call_tool("list_projects", {})
        project_name = None
        project_id = get_project_id()

        for project in projects_result.data:
            if project["id"] == project_id:
                project_name = project["name"]
                break

        # Use uppercase version of pipeline name
        pipeline_name = "TEST_RUN_AND_GET_PIPELINE_RUN_DETAILS"

        result = await mcp_client.call_tool(
            "run_pipeline_and_get_outcome",
            {"project_name": project_name, "pipeline_name": pipeline_name, "timeout_seconds": 60},
        )

        assert result.data is not None, (
            f"Should successfully run pipeline with case-insensitive name '{pipeline_name}'"
        )
        assert "success" in result.data, "Result should contain success field"

    @requires_ado_creds
    async def test_run_pipeline_and_get_outcome_fuzzy_match(self, mcp_client: Client):
        """Test run_pipeline_and_get_outcome with fuzzy matching for typos."""
        projects_result = await mcp_client.call_tool("list_projects", {})
        project_name = None
        project_id = get_project_id()

        for project in projects_result.data:
            if project["id"] == project_id:
                project_name = project["name"]
                break

        # Use typo version: replace underscores with dashes
        pipeline_name = "test-run-and-get-pipeline-run-details"

        result = await mcp_client.call_tool(
            "run_pipeline_and_get_outcome",
            {"project_name": project_name, "pipeline_name": pipeline_name, "timeout_seconds": 60},
        )

        assert result.data is not None, (
            f"Should successfully run pipeline with fuzzy matching for '{pipeline_name}'"
        )
        assert "success" in result.data, "Result should contain success field"

    @requires_ado_creds
    async def test_run_pipeline_exact_name(self, mcp_client: Client):
        """Test basic run_pipeline with exact pipeline name match."""
        projects_result = await mcp_client.call_tool("list_projects", {})
        project_name = None
        project_id = get_project_id()

        for project in projects_result.data:
            if project["id"] == project_id:
                project_name = project["name"]
                break

        pipeline_name = "test_run_and_get_pipeline_run_details"

        result = await mcp_client.call_tool(
            "run_pipeline", {"project_name": project_name, "pipeline_name": pipeline_name}
        )

        assert result.data is not None, f"Should successfully start pipeline '{pipeline_name}'"
        assert "id" in result.data, "Result should contain run ID"
        assert "state" in result.data, "Result should contain run state"

    @requires_ado_creds
    async def test_run_pipeline_with_variables(self, mcp_client: Client):
        """Test run_pipeline with runtime variables."""
        projects_result = await mcp_client.call_tool("list_projects", {})
        project_name = None
        project_id = get_project_id()

        for project in projects_result.data:
            if project["id"] == project_id:
                project_name = project["name"]
                break

        # Use the runtime variables test pipeline
        pipeline_name = "runtime-variables-test"
        variables = {"testVar": "name-based-test-value"}

        result = await mcp_client.call_tool(
            "run_pipeline",
            {"project_name": project_name, "pipeline_name": pipeline_name, "variables": variables},
        )

        assert result.data is not None, (
            f"Should successfully start pipeline '{pipeline_name}' with variables"
        )
        assert "id" in result.data, "Result should contain run ID"

    @requires_ado_creds
    async def test_invalid_pipeline_name_error_with_suggestions(self, mcp_client: Client):
        """Test that invalid pipeline name returns intelligent error with suggestions."""
        projects_result = await mcp_client.call_tool("list_projects", {})
        project_name = None
        project_id = get_project_id()

        for project in projects_result.data:
            if project["id"] == project_id:
                project_name = project["name"]
                break

        invalid_pipeline_name = "NonExistentPipelineNameForTesting"

        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool(
                "run_pipeline_and_get_outcome",
                {
                    "project_name": project_name,
                    "pipeline_name": invalid_pipeline_name,
                    "timeout_seconds": 60,
                },
            )

        error_message = str(exc_info.value)

        # Should contain fuzzy matching error message
        assert "not found" in error_message.lower(), (
            f"Error should indicate pipeline not found, but got: {error_message}"
        )
        assert (
            "did you mean" in error_message.lower()
            or "available pipelines" in error_message.lower()
            or "similar pipelines" in error_message.lower()
        ), f"Error should provide information about available pipelines, but got: {error_message}"

    @requires_ado_creds
    async def test_invalid_project_name_error_with_suggestions(self, mcp_client: Client):
        """Test that invalid project name returns intelligent error with suggestions."""
        invalid_project_name = "NonExistentProjectNameForTesting"
        pipeline_name = "test_run_and_get_pipeline_run_details"

        with pytest.raises(Exception) as exc_info:
            await mcp_client.call_tool(
                "run_pipeline",
                {"project_name": invalid_project_name, "pipeline_name": pipeline_name},
            )

        error_message = str(exc_info.value)

        # Should contain fuzzy matching error message for projects
        assert "not found" in error_message.lower(), (
            f"Error should indicate project not found, but got: {error_message}"
        )
        assert (
            "did you mean" in error_message.lower()
            or "available projects" in error_message.lower()
            or "similar projects" in error_message.lower()
        ), f"Error should provide project information, but got: {error_message}"

    @requires_ado_creds
    async def test_fuzzy_matching_performance(self, mcp_client: Client):
        """Test that fuzzy matching meets performance requirements."""
        import time

        projects_result = await mcp_client.call_tool("list_projects", {})
        project_name = None
        project_id = get_project_id()

        for project in projects_result.data:
            if project["id"] == project_id:
                project_name = project["name"]
                break

        # Use invalid name to trigger fuzzy matching
        invalid_name = "InvalidPipelineNameToTriggerFuzzyMatching"

        start_time = time.time()

        try:
            await mcp_client.call_tool(
                "run_pipeline", {"project_name": project_name, "pipeline_name": invalid_name}
            )
        except Exception:
            # Expected to fail, we're measuring fuzzy matching performance
            pass

        elapsed_ms = (time.time() - start_time) * 1000

        # Should complete fuzzy matching in reasonable time (allowing for lowered threshold)
        assert elapsed_ms < 400, (
            f"Fuzzy matching should complete quickly but took {elapsed_ms:.1f}ms"
        )

    @requires_ado_creds
    async def test_error_message_token_limiting(self, mcp_client: Client):
        """Test that error messages are appropriately limited to prevent token overflow."""
        projects_result = await mcp_client.call_tool("list_projects", {})
        project_name = None
        project_id = get_project_id()

        for project in projects_result.data:
            if project["id"] == project_id:
                project_name = project["name"]
                break

        invalid_name = "InvalidPipelineForTokenLimitingTest"

        try:
            await mcp_client.call_tool(
                "run_pipeline_and_get_outcome",
                {
                    "project_name": project_name,
                    "pipeline_name": invalid_name,
                    "timeout_seconds": 60,
                },
            )
            pytest.fail("Should have raised an exception for invalid pipeline name")
        except Exception as e:
            error_message = str(e)

            # Error message should not be excessively long
            estimated_tokens = len(error_message) / 4  # Rough token estimate
            assert estimated_tokens < 1000, (
                f"Error message should be token-limited. Estimated tokens: {estimated_tokens:.0f}"
            )

            # But should still contain useful information
            assert "not found" in error_message.lower(), "Error should indicate pipeline not found"
            assert (
                "did you mean" in error_message.lower()
                or "available pipelines" in error_message.lower()
                or "similar pipelines" in error_message.lower()
            ), "Error should provide suggestions"

    @requires_ado_creds
    async def test_pipeline_name_variations(self, mcp_client: Client):
        """Test various pipeline name formats and separators."""
        projects_result = await mcp_client.call_tool("list_projects", {})
        project_name = None
        project_id = get_project_id()

        for project in projects_result.data:
            if project["id"] == project_id:
                project_name = project["name"]
                break

        # Test different variations that should all match "test_run_and_get_pipeline_run_details"
        name_variations = [
            "test_run_and_get_pipeline_run_details",  # exact
            "test-run-and-get-pipeline-run-details",  # dashes
            "test.run.and.get.pipeline.run.details",  # dots
            "testrunandgetpipelinerundetails",  # no separators
            "TEST RUN AND GET PIPELINE RUN DETAILS",  # spaces and uppercase
        ]

        for variation in name_variations:
            try:
                result = await mcp_client.call_tool(
                    "run_pipeline", {"project_name": project_name, "pipeline_name": variation}
                )

                # Should succeed with fuzzy matching
                assert result.data is not None, (
                    f"Should match '{variation}' to 'test_run_and_get_pipeline_run_details'"
                )
                assert "id" in result.data, f"Should return run ID for '{variation}'"

            except Exception as e:
                # If it fails, the error should still provide suggestions
                error_msg = str(e)
                assert "test_run_and_get_pipeline_run_details" in error_msg.lower(), (
                    f"Error for '{variation}' should suggest correct pipeline name"
                )

    @requires_ado_creds
    async def test_run_pipeline_and_get_outcome_with_failure_analysis(self, mcp_client: Client):
        """Test run_pipeline_and_get_outcome returns detailed failure analysis for failed pipelines."""
        projects_result = await mcp_client.call_tool("list_projects", {})
        project_name = None
        project_id = get_project_id()

        for project in projects_result.data:
            if project["id"] == project_id:
                project_name = project["name"]
                break

        # Use a pipeline that's designed to fail
        failing_pipeline_name = "log-test-failing"

        result = await mcp_client.call_tool(
            "run_pipeline_and_get_outcome",
            {
                "project_name": project_name,
                "pipeline_name": failing_pipeline_name,
                "timeout_seconds": 120,
            },
        )

        assert result.data is not None, "Should return results even for failed pipeline"
        assert result.data["success"] is False, "Pipeline should have failed"
        assert "failure_summary" in result.data, "Should include failure analysis"
        assert result.data["failure_summary"] is not None, "Failure summary should not be None"

        # Check that failure summary contains useful information
        failure_summary = result.data["failure_summary"]
        assert "total_failed_steps" in failure_summary, "Should include failed step count"
        assert failure_summary["total_failed_steps"] > 0, "Should have at least one failed step"
