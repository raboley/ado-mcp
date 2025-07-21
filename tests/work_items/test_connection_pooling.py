"""Tests for connection pooling functionality in ADO client."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from requests.adapters import HTTPAdapter

from ado.client import AdoClient
from ado.work_items.client import WorkItemsClient
from ado.config import AdoMcpConfig, ConnectionPoolConfig


@pytest.fixture
def pooled_config():
    """Create a configuration with connection pooling enabled."""
    config = AdoMcpConfig()
    config.connection_pool.enabled = True
    config.connection_pool.max_pool_connections = 10
    config.connection_pool.max_pool_size = 50
    config.connection_pool.block = False
    config.connection_pool.pool_timeout = 2.0
    return config


@pytest.fixture
def non_pooled_config():
    """Create a configuration with connection pooling disabled."""
    config = AdoMcpConfig()
    config.connection_pool.enabled = False
    return config


@pytest.fixture
def mock_auth_manager():
    """Mock the AuthManager to avoid authentication setup during tests."""
    with patch('ado.auth.AuthManager') as mock_auth:
        mock_auth.return_value.get_auth_headers.return_value = {
            'Authorization': 'Basic dGVzdA==',
            'Content-Type': 'application/json'
        }
        mock_auth.return_value.get_auth_method.return_value = 'pat'
        yield mock_auth


class TestConnectionPooling:
    
    def test_client_creates_session_when_pooling_enabled(self, pooled_config, mock_auth_manager):
        """Test that client creates a session when connection pooling is enabled."""
        client = AdoClient(
            organization_url='https://dev.azure.com/test',
            pat='test-pat',
            config=pooled_config
        )
        
        assert hasattr(client, 'session')
        assert isinstance(client.session, requests.Session)
        assert client.session != requests  # Should be a Session instance, not the module
    
    def test_client_uses_requests_module_when_pooling_disabled(self, non_pooled_config, mock_auth_manager):
        """Test that client uses requests module when connection pooling is disabled."""
        client = AdoClient(
            organization_url='https://dev.azure.com/test',
            pat='test-pat',
            config=non_pooled_config
        )
        
        assert hasattr(client, 'session')
        assert client.session == requests  # Should be the requests module
    
    def test_session_configured_with_pool_settings(self, pooled_config, mock_auth_manager):
        """Test that session is configured with correct pooling settings."""
        with patch('ado.client.requests.Session') as mock_session_class, \
             patch('ado.client.HTTPAdapter') as mock_adapter_class:
            
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            
            mock_adapter = Mock()
            mock_adapter_class.return_value = mock_adapter
            
            client = AdoClient(
                organization_url='https://dev.azure.com/test',
                pat='test-pat',
                config=pooled_config
            )
            
            # Verify HTTPAdapter was created with correct settings
            mock_adapter_class.assert_called_once_with(
                pool_connections=10,
                pool_maxsize=50,
                pool_block=False
            )
            
            # Verify adapters were mounted
            assert mock_session.mount.call_count == 2
            mock_session.mount.assert_any_call('http://', mock_adapter)
            mock_session.mount.assert_any_call('https://', mock_adapter)
    
    def test_send_request_uses_session_when_available(self, pooled_config, mock_auth_manager):
        """Test that _send_request uses session when available."""
        with patch('ado.client.requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            
            # Mock successful response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = True
            mock_response.json.return_value = {'test': 'data'}
            mock_response.raise_for_status.return_value = None
            mock_session.request.return_value = mock_response
            
            client = AdoClient(
                organization_url='https://dev.azure.com/test',
                pat='test-pat',
                config=pooled_config
            )
            
            # Make a request
            result = client._send_request(
                method="GET",
                url="https://dev.azure.com/test/_apis/test"
            )
            
            # Verify session.request was called, not requests.request
            mock_session.request.assert_called_once()
            assert result == {'test': 'data'}
    
    def test_work_items_client_uses_session_for_create_operations(self, pooled_config, mock_auth_manager):
        """Test that work items client uses session for create operations."""
        with patch('ado.client.requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            
            # Mock successful response with proper WorkItem fields
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = True
            mock_response.json.return_value = {
                'id': 123,
                'rev': 1,
                'url': 'https://dev.azure.com/test/_apis/wit/workItems/123',
                'fields': {
                    'System.Title': 'Test Bug',
                    'System.WorkItemType': 'Bug',
                    'System.State': 'New'
                }
            }
            mock_response.raise_for_status.return_value = None
            mock_session.request.return_value = mock_response
            
            client = AdoClient(
                organization_url='https://dev.azure.com/test',
                pat='test-pat',
                config=pooled_config
            )
            work_items_client = WorkItemsClient(client)
            
            # Create work item
            result = work_items_client.create_work_item(
                project_id="test-project",
                work_item_type="Bug",
                fields={"System.Title": "Test Bug"}
            )
            
            # Verify session was used for the request
            mock_session.request.assert_called()
            assert result.id == 123
    
    def test_work_items_client_uses_session_for_update_operations(self, pooled_config, mock_auth_manager):
        """Test that work items client uses session for update operations."""
        with patch('ado.client.requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            
            # Mock successful response with proper WorkItem fields
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = True
            mock_response.json.return_value = {
                'id': 123,
                'rev': 2,
                'url': 'https://dev.azure.com/test/_apis/wit/workItems/123',
                'fields': {
                    'System.Title': 'Updated Bug',
                    'System.WorkItemType': 'Bug',
                    'System.State': 'Active'
                }
            }
            mock_response.raise_for_status.return_value = None
            mock_session.request.return_value = mock_response
            
            client = AdoClient(
                organization_url='https://dev.azure.com/test',
                pat='test-pat',
                config=pooled_config
            )
            work_items_client = WorkItemsClient(client)
            
            # Update work item
            from ado.work_items.models import JsonPatchOperation
            operations = [
                JsonPatchOperation(op="replace", path="/fields/System.Title", value="Updated Bug")
            ]
            
            result = work_items_client.update_work_item(
                project_id="test-project",
                work_item_id=123,
                operations=operations
            )
            
            # Verify session was used for the request
            mock_session.request.assert_called()
            assert result.id == 123
    
    def test_client_context_manager_closes_session(self, pooled_config, mock_auth_manager):
        """Test that client context manager properly closes session."""
        with patch('ado.client.requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            
            # Use client as context manager
            with AdoClient(
                organization_url='https://dev.azure.com/test',
                pat='test-pat',
                config=pooled_config
            ) as client:
                assert hasattr(client, 'session')
                assert client.session == mock_session
            
            # Verify session.close was called
            mock_session.close.assert_called_once()
    
    def test_client_manual_close_closes_session(self, pooled_config, mock_auth_manager):
        """Test that manual client.close() properly closes session."""
        with patch('ado.client.requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            
            client = AdoClient(
                organization_url='https://dev.azure.com/test',
                pat='test-pat',
                config=pooled_config
            )
            
            client.close()
            
            # Verify session.close was called
            mock_session.close.assert_called_once()
    
    def test_client_close_handles_no_session_gracefully(self, non_pooled_config, mock_auth_manager):
        """Test that close() handles cases where session is requests module."""
        client = AdoClient(
            organization_url='https://dev.azure.com/test',
            pat='test-pat',
            config=non_pooled_config
        )
        
        # Should not raise an exception
        client.close()
    
    def test_connection_pool_config_validation(self):
        """Test that connection pool configuration is properly validated."""
        # Valid configuration should work
        valid_config = ConnectionPoolConfig(
            enabled=True,
            max_pool_connections=10,
            max_pool_size=50,
            block=False,
            pool_timeout=5.0
        )
        assert valid_config.enabled
        
        # Invalid max_pool_connections
        with pytest.raises(Exception):  # Should raise AdoConfigurationError
            ConnectionPoolConfig(max_pool_connections=0)
        
        # Invalid max_pool_size  
        with pytest.raises(Exception):  # Should raise AdoConfigurationError
            ConnectionPoolConfig(max_pool_size=-1)
        
        # Invalid pool_timeout
        with pytest.raises(Exception):  # Should raise AdoConfigurationError
            ConnectionPoolConfig(pool_timeout=0)
    
    def test_fallback_to_requests_when_session_unavailable(self, pooled_config, mock_auth_manager):
        """Test fallback to requests module when session is not available."""
        with patch('requests.request') as mock_requests_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = True
            mock_response.json.return_value = {'test': 'data'}
            mock_requests_request.return_value = mock_response
            
            client = AdoClient(
                organization_url='https://dev.azure.com/test',
                pat='test-pat',
                config=pooled_config
            )
            
            # Simulate session being unavailable
            client.session = requests  # Set to module instead of Session instance
            work_items_client = WorkItemsClient(client)
            
            # This should fall back to requests.request
            work_items_client.create_work_item(
                project_id="test-project",
                work_item_type="Bug",
                fields={"System.Title": "Test Bug"}
            )
            
            # Verify requests.request was called as fallback
            mock_requests_request.assert_called()