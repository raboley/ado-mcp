"""
Dynamic test configuration fixtures for ado-mcp tests.

This module provides pytest fixtures that replace hardcoded values with dynamic
lookups from the Terraform-generated configuration.
"""

from typing import Any

import pytest

from src.test_config import (
    ConfigError,
    get_test_config,
)


@pytest.fixture(scope="session")
def test_config():
    """
    Session-scoped fixture that provides the test configuration.

    Returns:
        TestConfig instance

    Raises:
        pytest.skip: If no test configuration is available
    """
    try:
        return get_test_config()
    except ConfigError as e:
        pytest.skip(
            f"Test configuration not available: {e}. Run 'task ado-up' to provision test environment."
        )


@pytest.fixture(scope="session")
def test_project_id(test_config) -> str:
    """Get the test project ID dynamically."""
    return test_config.project_id


@pytest.fixture(scope="session")
def test_project_name(test_config) -> str:
    """Get the test project name dynamically."""
    return test_config.project_name


@pytest.fixture(scope="session")
def test_organization_url(test_config) -> str:
    """Get the test organization URL dynamically."""
    return test_config.organization_url


# Pipeline ID fixtures with graceful fallback
@pytest.fixture(scope="session")
def basic_pipeline_id(test_config) -> int:
    """Get the basic test pipeline ID (test_run_and_get_pipeline_run_details)."""
    try:
        return test_config.get_pipeline_id("test_run_and_get_pipeline_run_details")
    except ConfigError:
        pytest.skip("Basic test pipeline not found. Ensure pipelines are set up in Azure DevOps.")


@pytest.fixture(scope="session")
def complex_pipeline_id(test_config) -> int:
    """Get the complex test pipeline ID (slow.log-test-complex)."""
    try:
        return test_config.get_pipeline_id("slow.log-test-complex")
    except ConfigError:
        pytest.skip("Complex test pipeline not found. Ensure pipelines are set up in Azure DevOps.")


@pytest.fixture(scope="session")
def failing_pipeline_id(test_config) -> int:
    """Get the failing test pipeline ID (log-test-failing)."""
    try:
        return test_config.get_pipeline_id("log-test-failing")
    except ConfigError:
        pytest.skip("Failing test pipeline not found. Ensure pipelines are set up in Azure DevOps.")


@pytest.fixture(scope="session")
def parameterized_pipeline_id(test_config) -> int:
    """Get the parameterized preview test pipeline ID (preview-test-parameterized)."""
    try:
        return test_config.get_pipeline_id("preview-test-parameterized")
    except ConfigError:
        pytest.skip(
            "Parameterized test pipeline not found. Ensure pipelines are set up in Azure DevOps."
        )


@pytest.fixture(scope="session")
def preview_pipeline_id(test_config) -> int:
    """Get the basic preview test pipeline ID (preview-test-valid)."""
    try:
        return test_config.get_pipeline_id("preview-test-valid")
    except ConfigError:
        pytest.skip("Preview test pipeline not found. Ensure pipelines are set up in Azure DevOps.")


@pytest.fixture(scope="session")
def github_resources_pipeline_id(test_config) -> int:
    """Get the GitHub resources test pipeline ID (github-resources-test-stable)."""
    try:
        return test_config.get_pipeline_id("github-resources-test-stable")
    except ConfigError:
        pytest.skip(
            "GitHub resources test pipeline not found. Ensure pipelines are set up in Azure DevOps."
        )


@pytest.fixture(scope="session")
def runtime_variables_pipeline_id(test_config) -> int:
    """Get the runtime variables test pipeline ID (runtime-variables-test)."""
    try:
        return test_config.get_pipeline_id("runtime-variables-test")
    except ConfigError:
        pytest.skip(
            "Runtime variables test pipeline not found. Ensure pipelines are set up in Azure DevOps."
        )


# Legacy constant replacements for backward compatibility
@pytest.fixture(scope="session")
def TEST_PROJECT_ID(test_project_id) -> str:
    """Legacy fixture name for backward compatibility."""
    return test_project_id


@pytest.fixture(scope="session")
def BASIC_PIPELINE_ID(basic_pipeline_id) -> int:
    """Legacy fixture name for backward compatibility."""
    return basic_pipeline_id


# Convenience fixtures for common test patterns
@pytest.fixture(scope="session")
def pipeline_ids(test_config) -> dict[str, int]:
    """
    Get all available pipeline IDs as a dictionary.

    Returns:
        Dictionary mapping pipeline names to IDs
    """
    pipeline_ids = {}

    pipeline_names = test_config.get_all_pipeline_names()
    for name in pipeline_names:
        try:
            pipeline_ids[name] = test_config.get_pipeline_id(name)
        except ConfigError:
            # Skip pipelines that aren't properly configured
            continue

    return pipeline_ids


@pytest.fixture(scope="session")
def available_pipelines(test_config) -> list[str]:
    """Get list of all available pipeline names."""
    return test_config.get_all_pipeline_names()


@pytest.fixture(scope="session")
def test_environment_status(test_config) -> dict[str, Any]:
    """
    Get comprehensive test environment status.

    Returns:
        Dictionary with environment validation results
    """
    from src.test_config import validate_test_environment

    return validate_test_environment()


# Environment validation fixture
@pytest.fixture(scope="session", autouse=True)
def validate_test_environment_setup(test_config):
    """
    Automatically validate test environment setup at session start.

    This fixture runs automatically and provides warnings if the environment
    is not properly configured.
    """
    from src.test_config import validate_test_environment

    validation = validate_test_environment()

    if not validation.get("config_loaded", False):
        pytest.skip(
            f"Test environment not configured: {validation.get('error')}. {validation.get('suggestion', '')}"
        )

    # Log about placeholder pipeline IDs but don't fail
    if validation.get("needs_manual_setup", False):
        import logging
        
        logger = logging.getLogger(__name__)
        logger.info(
            f"Some pipelines need manual setup: {validation.get('errors', [])}. "
            "Tests using these pipelines will be skipped."
        )


# Backward compatibility - provide constants for existing tests
def pytest_configure():
    """Set up backward compatibility constants."""
    try:
        config = get_test_config()

        # Set module-level constants for backward compatibility
        import sys

        current_module = sys.modules[__name__]

        # Set project constants
        current_module.TEST_PROJECT_ID = config.project_id
        current_module.PROJECT_NAME = config.project_name

        # Set pipeline constants with fallbacks
        pipeline_mappings = {
            "BASIC_PIPELINE_ID": "test_run_and_get_pipeline_run_details",
            "COMPLEX_PIPELINE_ID": "slow.log-test-complex",
            "FAILING_PIPELINE_ID": "log-test-failing",
            "PARAMETERIZED_PIPELINE_ID": "preview-test-parameterized",
            "PREVIEW_PIPELINE_ID": "preview-test-valid",
            "GITHUB_RESOURCES_PIPELINE_ID": "github-resources-test-stable",
            "RUNTIME_VARIABLES_PIPELINE_ID": "runtime-variables-test",
        }

        for const_name, pipeline_name in pipeline_mappings.items():
            try:
                pipeline_id = config.get_pipeline_id(pipeline_name)
                setattr(current_module, const_name, pipeline_id)
            except ConfigError:
                # Set placeholder value - tests will skip if they need this pipeline
                setattr(current_module, const_name, 999)

    except ConfigError:
        # If config is not available, set placeholder values
        # Tests will be skipped by the fixtures above
        pass
