import pytest
import os
from ado_client import AdoClient

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
    try:
        connection_data = ado_client.check_authentication()
        assert connection_data is not None
        assert "authenticatedUser" in connection_data
        assert "id" in connection_data["authenticatedUser"]
        print(f"Successfully authenticated as user ID: {connection_data['authenticatedUser']['id']}")
    except Exception as e:
        pytest.fail(f"Authentication failed: {e}")
