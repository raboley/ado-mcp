"""
Dynamic test configuration system for ado-mcp.

This module provides utilities for loading test configuration from Terraform outputs
and resolving resource names to IDs dynamically, eliminating hardcoded test values.
"""

import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Raised when test configuration cannot be loaded or is invalid."""
    pass


class ResourceNotFoundError(Exception):
    """Raised when a required test resource cannot be found."""
    pass


class DynamicTestConfig:
    """
    Manages dynamic test configuration for ado-mcp tests.
    
    Loads configuration from Terraform outputs and provides utilities for
    resolving resource names to IDs dynamically.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize test configuration.
        
        Args:
            config_path: Optional path to configuration file. If not provided,
                        will look for terraform_config.json in tests directory.
        """
        self.config_path = config_path or self._get_default_config_path()
        self._config: Optional[Dict[str, Any]] = None
        self._load_config()
    
    def _get_default_config_path(self) -> str:
        """Get the default path to the Terraform configuration file."""
        # Look for config file relative to this module
        current_dir = Path(__file__).parent
        project_root = current_dir.parent
        config_path = project_root / "tests" / "terraform_config.json"
        return str(config_path)
    
    def _load_config(self) -> None:
        """Load configuration from file with comprehensive error handling."""
        try:
            if not os.path.exists(self.config_path):
                raise ConfigError(
                    f"Configuration file not found at {self.config_path}. "
                    "Run 'task ado-up' to provision test environment."
                )
            
            with open(self.config_path, 'r') as f:
                self._config = json.load(f)
            
            logger.info(f"Loaded test configuration from {self.config_path}")
            self._validate_config()
            
        except json.JSONDecodeError as e:
            raise ConfigError(
                f"Invalid JSON in configuration file {self.config_path}: {e}"
            )
        except Exception as e:
            raise ConfigError(
                f"Failed to load configuration from {self.config_path}: {e}"
            )
    
    def _validate_config(self) -> None:
        """Validate that required configuration sections exist."""
        if not self._config:
            raise ConfigError("Configuration is empty")
        
        required_sections = ["project", "pipelines", "organization_url"]
        missing_sections = [
            section for section in required_sections 
            if section not in self._config
        ]
        
        if missing_sections:
            raise ConfigError(
                f"Missing required configuration sections: {missing_sections}"
            )
        
        # Validate project section
        project = self._config["project"]
        if not all(key in project for key in ["id", "name"]):
            raise ConfigError(
                "Project configuration missing required fields: id, name"
            )
        
        logger.info(f"Configuration validated for project: {project['name']}")
    
    @property
    def project_id(self) -> str:
        """Get the test project ID."""
        return self._config["project"]["id"]
    
    @property
    def project_name(self) -> str:
        """Get the test project name."""
        return self._config["project"]["name"]
    
    @property
    def organization_url(self) -> str:
        """Get the Azure DevOps organization URL."""
        return self._config["organization_url"]
    
    def get_pipeline_id(self, pipeline_name: str) -> int:
        """
        Get pipeline ID by name.
        
        Args:
            pipeline_name: Name of the pipeline
            
        Returns:
            Pipeline ID
            
        Raises:
            ResourceNotFoundError: If pipeline not found
        """
        pipelines = self._config.get("pipelines", {})
        
        if pipeline_name not in pipelines:
            available_pipelines = list(pipelines.keys())
            raise ResourceNotFoundError(
                f"Pipeline '{pipeline_name}' not found in configuration. "
                f"Available pipelines: {available_pipelines}. "
                "Ensure all required pipelines are set up in Azure DevOps."
            )
        
        pipeline_config = pipelines[pipeline_name]
        pipeline_id = pipeline_config.get("id")
        
        if pipeline_id is None:
            raise ResourceNotFoundError(
                f"Pipeline '{pipeline_name}' exists in configuration but has no ID. "
                "This may indicate the pipeline was not properly created."
            )
        
        logger.debug(f"Resolved pipeline '{pipeline_name}' to ID {pipeline_id}")
        return int(pipeline_id)
    
    def get_pipeline_config(self, pipeline_name: str) -> Dict[str, Any]:
        """
        Get complete pipeline configuration by name.
        
        Args:
            pipeline_name: Name of the pipeline
            
        Returns:
            Pipeline configuration dictionary
        """
        pipelines = self._config.get("pipelines", {})
        
        if pipeline_name not in pipelines:
            available_pipelines = list(pipelines.keys())
            raise ResourceNotFoundError(
                f"Pipeline '{pipeline_name}' not found. "
                f"Available: {available_pipelines}"
            )
        
        return pipelines[pipeline_name]
    
    def get_all_pipeline_names(self) -> list[str]:
        """Get list of all available pipeline names."""
        return list(self._config.get("pipelines", {}).keys())
    
    def get_service_connection_id(self, connection_name: str) -> str:
        """
        Get service connection ID by name.
        
        Args:
            connection_name: Name of the service connection
            
        Returns:
            Service connection ID
        """
        connections = self._config.get("service_connections", {})
        
        if connection_name not in connections:
            available_connections = list(connections.keys())
            raise ResourceNotFoundError(
                f"Service connection '{connection_name}' not found. "
                f"Available: {available_connections}"
            )
        
        return connections[connection_name]
    
    def has_pipeline(self, pipeline_name: str) -> bool:
        """Check if a pipeline exists in the configuration."""
        return pipeline_name in self._config.get("pipelines", {})
    
    def has_service_connection(self, connection_name: str) -> bool:
        """Check if a service connection exists in the configuration."""
        return connection_name in self._config.get("service_connections", {})


# Global test configuration instance
_test_config: Optional["DynamicTestConfig"] = None


@lru_cache(maxsize=1)
def get_test_config() -> "DynamicTestConfig":
    """
    Get the global test configuration instance.
    
    Returns:
        DynamicTestConfig instance
        
    Raises:
        ConfigError: If configuration cannot be loaded
    """
    global _test_config
    if _test_config is None:
        _test_config = DynamicTestConfig()
    return _test_config


def get_project_id() -> str:
    """Get the test project ID."""
    return get_test_config().project_id


def get_project_name() -> str:
    """Get the test project name."""
    return get_test_config().project_name


def get_pipeline_id(pipeline_name: str) -> int:
    """Get pipeline ID by name."""
    return get_test_config().get_pipeline_id(pipeline_name)


def get_organization_url() -> str:
    """Get the Azure DevOps organization URL."""
    return get_test_config().organization_url


# Convenience constants for commonly used pipelines
# These will be resolved dynamically from the configuration

def get_basic_pipeline_id() -> int:
    """Get ID for the basic test pipeline."""
    return get_pipeline_id("test_run_and_get_pipeline_run_details")


def get_complex_pipeline_id() -> int:
    """Get ID for the complex test pipeline."""
    return get_pipeline_id("slow.log-test-complex")


def get_failing_pipeline_id() -> int:
    """Get ID for the failing test pipeline."""
    return get_pipeline_id("log-test-failing")


def get_parameterized_pipeline_id() -> int:
    """Get ID for the parameterized preview test pipeline."""
    return get_pipeline_id("preview-test-parameterized")


def get_preview_pipeline_id() -> int:
    """Get ID for the basic preview test pipeline."""
    return get_pipeline_id("preview-test-valid")


def get_github_resources_pipeline_id() -> int:
    """Get ID for the GitHub resources test pipeline."""
    return get_pipeline_id("github-resources-test-stable")


def get_runtime_variables_pipeline_id() -> int:
    """Get ID for the runtime variables test pipeline."""
    return get_pipeline_id("runtime-variables-test")


# Test environment validation
def validate_test_environment() -> Dict[str, Any]:
    """
    Validate that the test environment is properly configured.
    
    Returns:
        Dictionary with validation results
    """
    try:
        config = get_test_config()
        
        validation_results = {
            "config_loaded": True,
            "project_configured": True,
            "project_id": config.project_id,
            "project_name": config.project_name,
            "organization_url": config.organization_url,
            "pipelines_count": len(config.get_all_pipeline_names()),
            "pipeline_names": config.get_all_pipeline_names(),
            "errors": []
        }
        
        # Check for placeholder pipeline IDs
        placeholder_pipelines = []
        for pipeline_name in config.get_all_pipeline_names():
            try:
                pipeline_id = config.get_pipeline_id(pipeline_name)
                if pipeline_id == 999:  # Placeholder ID
                    placeholder_pipelines.append(pipeline_name)
            except ResourceNotFoundError:
                validation_results["errors"].append(
                    f"Pipeline '{pipeline_name}' configuration is invalid"
                )
        
        if placeholder_pipelines:
            validation_results["errors"].append(
                f"Pipelines with placeholder IDs (need manual setup): {placeholder_pipelines}"
            )
        
        validation_results["needs_manual_setup"] = bool(placeholder_pipelines)
        
        return validation_results
        
    except ConfigError as e:
        return {
            "config_loaded": False,
            "error": str(e),
            "suggestion": "Run 'task ado-up' to provision test environment"
        }


# Backward compatibility aliases for tests
TestConfigError = ConfigError
TestResourceNotFoundError = ResourceNotFoundError
TestConfig = DynamicTestConfig