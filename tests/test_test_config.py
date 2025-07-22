"""
End-to-end tests for the dynamic test configuration system.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from src.test_config import (
    DynamicTestConfig,
    ConfigError,
    ResourceNotFoundError,
    get_basic_pipeline_id,
    get_project_id,
    get_project_name,
    get_test_config,
    validate_test_environment,
)


def test_load_valid_terraform_config():
    """Test loading a valid Terraform configuration file."""
    config_data = {
        "project": {
            "id": "test-project-id-123",
            "name": "ado-mcp2",
            "url": "https://dev.azure.com/test/ado-mcp2"
        },
        "pipelines": {
            "test_run_and_get_pipeline_run_details": {
                "id": 100,
                "name": "test_run_and_get_pipeline_run_details",
                "yaml_path": "tests/ado/fixtures/fast.test.pipeline.yml"
            },
            "slow.log-test-complex": {
                "id": 101,
                "name": "slow.log-test-complex",
                "yaml_path": "tests/ado/fixtures/complex-pipeline.yml"
            }
        },
        "service_connections": {
            "github-service-connection": "service-conn-123"
        },
        "organization_url": "https://dev.azure.com/TestOrg"
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        config_path = f.name
    
    try:
        config = DynamicTestConfig(config_path)
        
        assert config.project_id == "test-project-id-123"
        assert config.project_name == "ado-mcp2"
        assert config.organization_url == "https://dev.azure.com/TestOrg"
        
        assert config.get_pipeline_id("test_run_and_get_pipeline_run_details") == 100
        assert config.get_pipeline_id("slow.log-test-complex") == 101
        
        assert config.has_pipeline("test_run_and_get_pipeline_run_details") is True
        assert config.has_pipeline("nonexistent-pipeline") is False
        
        pipeline_names = config.get_all_pipeline_names()
        assert "test_run_and_get_pipeline_run_details" in pipeline_names
        assert "slow.log-test-complex" in pipeline_names
        
    finally:
        os.unlink(config_path)


def test_missing_config_file_error():
    """Test error handling when configuration file doesn't exist."""
    with pytest.raises(ConfigError) as exc_info:
        DynamicTestConfig("/nonexistent/path/config.json")
    
    assert "Configuration file not found" in str(exc_info.value)
    assert "task ado-up" in str(exc_info.value)


def test_invalid_json_error():
    """Test error handling for invalid JSON in configuration file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write("{ invalid json content")
        config_path = f.name
    
    try:
        with pytest.raises(ConfigError) as exc_info:
            DynamicTestConfig(config_path)
        
        assert "Invalid JSON" in str(exc_info.value)
        
    finally:
        os.unlink(config_path)


def test_missing_required_sections_error():
    """Test validation error for missing required configuration sections."""
    config_data = {
        "project": {
            "id": "test-id",
            "name": "test-name"
        }
        # Missing pipelines and organization_url
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        config_path = f.name
    
    try:
        with pytest.raises(ConfigError) as exc_info:
            DynamicTestConfig(config_path)
        
        assert "Missing required configuration sections" in str(exc_info.value)
        assert "pipelines" in str(exc_info.value)
        assert "organization_url" in str(exc_info.value)
        
    finally:
        os.unlink(config_path)


def test_pipeline_not_found_error():
    """Test error when requesting a pipeline that doesn't exist."""
    config_data = {
        "project": {"id": "test-id", "name": "test-name"},
        "pipelines": {"existing-pipeline": {"id": 100}},
        "organization_url": "https://dev.azure.com/test"
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        config_path = f.name
    
    try:
        config = DynamicTestConfig(config_path)
        
        with pytest.raises(ResourceNotFoundError) as exc_info:
            config.get_pipeline_id("nonexistent-pipeline")
        
        assert "Pipeline 'nonexistent-pipeline' not found" in str(exc_info.value)
        assert "Available pipelines: ['existing-pipeline']" in str(exc_info.value)
        
    finally:
        os.unlink(config_path)


def test_pipeline_missing_id_error():
    """Test error when pipeline exists but has no ID."""
    config_data = {
        "project": {"id": "test-id", "name": "test-name"},
        "pipelines": {
            "invalid-pipeline": {"name": "invalid-pipeline"}  # Missing ID
        },
        "organization_url": "https://dev.azure.com/test"
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        config_path = f.name
    
    try:
        config = DynamicTestConfig(config_path)
        
        with pytest.raises(ResourceNotFoundError) as exc_info:
            config.get_pipeline_id("invalid-pipeline")
        
        assert "has no ID" in str(exc_info.value)
        assert "not properly created" in str(exc_info.value)
        
    finally:
        os.unlink(config_path)


def test_convenience_functions_with_real_config():
    """Test convenience functions work with properly configured test environment."""
    # This test requires a real terraform_config.json file
    try:
        project_id = get_project_id()
        project_name = get_project_name()
        
        assert isinstance(project_id, str)
        assert len(project_id) > 0
        assert isinstance(project_name, str)
        assert len(project_name) > 0
        
        # Test that we can get pipeline IDs (may raise ResourceNotFoundError if not set up)
        try:
            basic_id = get_basic_pipeline_id()
            assert isinstance(basic_id, int)
            assert basic_id > 0
        except ResourceNotFoundError:
            # This is expected if pipelines aren't manually set up yet
            pass
            
    except ConfigError:
        # This is expected if terraform hasn't been run yet
        pytest.skip("No terraform configuration found - run 'task ado-up' first")


def test_validate_test_environment_success():
    """Test environment validation with properly configured environment."""
    try:
        results = validate_test_environment()
        
        assert results["config_loaded"] is True
        assert results["project_configured"] is True
        assert "project_id" in results
        assert "project_name" in results
        assert "organization_url" in results
        assert "pipelines_count" in results
        assert isinstance(results["pipeline_names"], list)
        
        # Check for placeholder warning
        if results.get("needs_manual_setup"):
            assert "errors" in results
            assert len(results["errors"]) > 0
            
    except ConfigError:
        pytest.skip("No terraform configuration found - run 'task ado-up' first")


def test_validate_test_environment_failure():
    """Test environment validation when configuration is missing."""
    # Temporarily move config file if it exists
    project_root = Path(__file__).parent.parent
    config_path = project_root / "tests" / "terraform_config.json"
    temp_path = None
    
    if config_path.exists():
        temp_path = config_path.with_suffix('.json.backup')
        config_path.rename(temp_path)
    
    try:
        # Clear cached config
        get_test_config.cache_clear()
        
        # Also clear the global variable
        import src.test_config
        src.test_config._test_config = None
        
        results = validate_test_environment()
        
        assert results["config_loaded"] is False
        assert "error" in results
        assert "suggestion" in results
        assert "task ado-up" in results["suggestion"]
        
    finally:
        # Restore config file if we moved it
        if temp_path and temp_path.exists():
            temp_path.rename(config_path)
        
        # Clear cache again to restore normal state
        get_test_config.cache_clear()


def test_get_pipeline_config_complete():
    """Test getting complete pipeline configuration."""
    config_data = {
        "project": {"id": "test-id", "name": "test-name"},
        "pipelines": {
            "test-pipeline": {
                "id": 100,
                "name": "test-pipeline",
                "yaml_path": "path/to/pipeline.yml",
                "description": "Test pipeline description"
            }
        },
        "organization_url": "https://dev.azure.com/test"
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        config_path = f.name
    
    try:
        config = DynamicTestConfig(config_path)
        pipeline_config = config.get_pipeline_config("test-pipeline")
        
        assert pipeline_config["id"] == 100
        assert pipeline_config["name"] == "test-pipeline"
        assert pipeline_config["yaml_path"] == "path/to/pipeline.yml"
        assert pipeline_config["description"] == "Test pipeline description"
        
    finally:
        os.unlink(config_path)


def test_service_connection_lookup():
    """Test service connection ID lookup."""
    config_data = {
        "project": {"id": "test-id", "name": "test-name"},
        "pipelines": {},
        "service_connections": {
            "github-service-connection": "conn-id-123",
            "other-connection": "conn-id-456"
        },
        "organization_url": "https://dev.azure.com/test"
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        config_path = f.name
    
    try:
        config = DynamicTestConfig(config_path)
        
        assert config.get_service_connection_id("github-service-connection") == "conn-id-123"
        assert config.has_service_connection("github-service-connection") is True
        assert config.has_service_connection("nonexistent") is False
        
        with pytest.raises(ResourceNotFoundError):
            config.get_service_connection_id("nonexistent")
            
    finally:
        os.unlink(config_path)