import pytest
import os
from ado_client import AdoClient, Pipeline

# You'll need to set ADO_ORGANIZATION_URL environment variable for this test
# For example: export ADO_ORGANIZATION_URL="https://dev.azure.com/your-organization"

@pytest.fixture(scope="module")
def ado_client():
    org_url = os.environ.get("ADO_ORGANIZATION_URL")
    if not org_url:
        pytest.skip("ADO_ORGANIZATION_URL environment variable not set.")
    return AdoClient(organization_url=org_url)

def test_authentication(ado_client):
    """Test that the AdoClient can successfully authenticate."""
    connection_data = ado_client.check_authentication()
    assert connection_data is not None
    assert "authenticatedUser" in connection_data
    assert "id" in connection_data["authenticatedUser"]
    print(f"Successfully authenticated as user ID: {connection_data['authenticatedUser']['id']}")

def test_ado_pat_not_set():
    """Test that AdoClient raises ValueError when AZURE_DEVOPS_EXT_PAT is not set."""
    original_pat = os.environ.get("AZURE_DEVOPS_EXT_PAT")
    if original_pat:
        del os.environ["AZURE_DEVOPS_EXT_PAT"]

    with pytest.raises(ValueError) as excinfo:
        AdoClient(organization_url="https://dev.azure.com/test-org")

    assert "AZURE_DEVOPS_EXT_PAT environment variable not set." in str(excinfo.value)

    if original_pat:
        os.environ["AZURE_DEVOPS_EXT_PAT"] = original_pat

def test_list_pipelines(ado_client):
    """Test that list_pipelines returns a list of Pipeline objects from a real API call."""
    project_name = "Learning"
    pipelines = ado_client.list_pipelines(project_name=project_name)

    expected_pipeline_count = 5

    assert isinstance(pipelines, list)
    assert len(pipelines) == expected_pipeline_count
    if expected_pipeline_count > 0:
        assert isinstance(pipelines[0], Pipeline)
        assert pipelines[0].id is not None
        assert pipelines[0].name is not None
    
