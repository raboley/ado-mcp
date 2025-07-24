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
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Base exception for test configuration errors."""

    __test__ = False  # Tell pytest this is not a test class
    pass


class ConfigFileNotFoundError(ConfigError):
    """Raised when the configuration file cannot be found."""

    pass


class ConfigValidationError(ConfigError):
    """Raised when configuration file exists but is invalid."""

    pass


class ConfigPermissionError(ConfigError):
    """Raised when configuration file cannot be read due to permissions."""

    pass


class ConfigParseError(ConfigError):
    """Raised when configuration file contains invalid JSON."""

    pass


class SimpleTestConfig:
    """
    Simple test configuration that provides only basic org/project info.

    Tests should use MCP tools like find_pipeline_by_name() instead of
    hardcoded pipeline IDs.
    """

    def __init__(self, config_path: str | None = None):
        """
        Initialize test configuration.

        Args:
            config_path: Optional path to configuration file. If not provided,
                        will look for terraform_config.json in tests directory.
        """
        self.config_path = config_path or self._get_default_config_path()
        self._config: dict[str, Any] | None = None
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
                raise ConfigFileNotFoundError(
                    f"Configuration file not found at {self.config_path}. "
                    "Run 'task ado-up' to provision test environment."
                )

            with open(self.config_path) as f:
                self._config = json.load(f)

            logger.info(f"Loaded test configuration from {self.config_path}")
            self._validate_config()

        except PermissionError as e:
            raise ConfigPermissionError(
                f"Permission denied reading configuration file {self.config_path}: {e}"
            )
        except json.JSONDecodeError as e:
            raise ConfigParseError(f"Invalid JSON in configuration file {self.config_path}: {e}")
        except ConfigError:
            # Re-raise our custom config errors
            raise
        except Exception as e:
            raise ConfigError(
                f"Unexpected error loading configuration from {self.config_path}: {e}"
            )

    def _validate_config(self) -> None:
        """Validate that required configuration sections exist."""
        if not self._config:
            raise ConfigValidationError("Configuration is empty")

        required_sections = ["project", "organization_url"]
        missing_sections = [section for section in required_sections if section not in self._config]

        if missing_sections:
            raise ConfigValidationError(
                f"Missing required configuration sections: {missing_sections}"
            )

        # Validate project section
        project = self._config["project"]
        if not all(key in project for key in ["id", "name"]):
            raise ConfigValidationError("Project configuration missing required fields: id, name")

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


def validate_test_environment() -> dict[str, Any]:
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
            "needs_manual_setup": False,
        }

    except ConfigFileNotFoundError as e:
        return {
            "config_loaded": False,
            "error": str(e),
            "error_type": "file_not_found",
            "suggestion": "Run 'task ado-up' to provision test environment",
        }
    except ConfigParseError as e:
        return {
            "config_loaded": False,
            "error": str(e),
            "error_type": "parse_error",
            "suggestion": "Check JSON syntax in terraform_config.json or re-run 'task ado-up'",
        }
    except ConfigValidationError as e:
        return {
            "config_loaded": False,
            "error": str(e),
            "error_type": "validation_error",
            "suggestion": "Configuration file is corrupt. Re-run 'task ado-up' to regenerate",
        }
    except ConfigPermissionError as e:
        return {
            "config_loaded": False,
            "error": str(e),
            "error_type": "permission_error",
            "suggestion": "Check file permissions on terraform_config.json",
        }
    except ConfigError as e:
        return {
            "config_loaded": False,
            "error": str(e),
            "error_type": "unknown",
            "suggestion": "Run 'task ado-up' to provision test environment",
        }


# Backward compatibility aliases
TestConfigError = ConfigError
DynamicTestConfig = SimpleTestConfig  # For backward compatibility
