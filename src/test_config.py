"""
Simple test configuration system for ado-mcp.

This module provides basic configuration for Azure DevOps organization and project info.
Tests use MCP tools directly to look up pipelines by name instead of hardcoded IDs.
"""

import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Raised when test configuration cannot be loaded or is invalid."""
    __test__ = False  # Tell pytest this is not a test class
    pass


class SimpleTestConfig:
    """
    Simple test configuration that provides only basic org/project info.
    
    Tests should use MCP tools like find_pipeline_by_name() instead of 
    hardcoded pipeline IDs.
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
        
        required_sections = ["project", "organization_url"]
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


# Global test configuration instance
_test_config: Optional["SimpleTestConfig"] = None


@lru_cache(maxsize=1)
def get_test_config() -> "SimpleTestConfig":
    """
    Get the global test configuration instance.
    
    Returns:
        SimpleTestConfig instance
        
    Raises:
        ConfigError: If configuration cannot be loaded
    """
    global _test_config
    if _test_config is None:
        _test_config = SimpleTestConfig()
    return _test_config


def get_project_id() -> str:
    """Get the test project ID."""
    return get_test_config().project_id


def get_project_name() -> str:
    """Get the test project name."""
    return get_test_config().project_name


def get_organization_url() -> str:
    """Get the Azure DevOps organization URL."""
    return get_test_config().organization_url


def validate_test_environment() -> Dict[str, Any]:
    """
    Validate that the test environment is properly configured.
    
    Returns:
        Dictionary with validation results
    """
    try:
        config = get_test_config()
        
        return {
            "config_loaded": True,
            "project_configured": True,
            "project_id": config.project_id,
            "project_name": config.project_name,
            "organization_url": config.organization_url,
            "errors": [],
            "needs_manual_setup": False
        }
        
    except ConfigError as e:
        return {
            "config_loaded": False,
            "error": str(e),
            "suggestion": "Run 'task ado-up' to provision test environment"
        }


# Backward compatibility aliases
TestConfigError = ConfigError
DynamicTestConfig = SimpleTestConfig  # For backward compatibility