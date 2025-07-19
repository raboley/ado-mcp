"""
Test environment variable loading for IDE compatibility.

This test verifies that .env variables are properly loaded regardless
of how tests are executed (pytest CLI, IDE, etc.).
"""

import os
import pytest


def test_environment_variables_loaded():
    """Test that required environment variables are loaded from .env file."""
    # Test that ADO credentials are available
    ado_pat = os.getenv("AZURE_DEVOPS_EXT_PAT")
    ado_org_url = os.getenv("ADO_ORGANIZATION_URL")
    
    # These should be loaded from .env file
    assert ado_pat is not None, "AZURE_DEVOPS_EXT_PAT should be loaded from .env file"
    assert ado_org_url is not None, "ADO_ORGANIZATION_URL should be loaded from .env file"
    
    # Verify they have reasonable values
    assert ado_pat.strip() != "", "AZURE_DEVOPS_EXT_PAT should not be empty"
    assert ado_org_url.startswith("https://"), "ADO_ORGANIZATION_URL should be a valid URL"
    
    print(f"✓ AZURE_DEVOPS_EXT_PAT: {'*' * (len(ado_pat) - 4)}{ado_pat[-4:]}")
    print(f"✓ ADO_ORGANIZATION_URL: {ado_org_url}")


def test_optional_environment_variables():
    """Test optional environment variables from .env file."""
    ado_project_name = os.getenv("ADO_PROJECT_NAME")
    
    if ado_project_name:
        print(f"✓ ADO_PROJECT_NAME: {ado_project_name}")
        assert ado_project_name.strip() != "", "ADO_PROJECT_NAME should not be empty if set"
    else:
        print("ℹ ADO_PROJECT_NAME not set (optional)")


@pytest.mark.skipif(
    not all([os.getenv("AZURE_DEVOPS_EXT_PAT"), os.getenv("ADO_ORGANIZATION_URL")]),
    reason="Skipping: ADO credentials not available"
)
def test_environment_ready_for_ado_tests():
    """Test that environment is properly configured for Azure DevOps tests."""
    from tests.ado.test_client import requires_ado_creds
    
    # This test should not be skipped if environment is properly loaded
    print("✓ Environment is ready for Azure DevOps integration tests")
    print("✓ @requires_ado_creds decorator should allow tests to run")