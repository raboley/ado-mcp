#!/usr/bin/env python3
"""
Version management script for ado-mcp package.

This script fetches the latest version from PyPI and calculates the next patch version.
"""

import json
import re
import sys
from urllib.error import HTTPError
from urllib.request import urlopen


def get_latest_version_from_pypi(package_name: str) -> str | None:
    """
    Fetch the latest version of a package from PyPI.

    Args:
        package_name (str): The name of the package on PyPI

    Returns:
        str | None: The latest version string, or None if not found
    """
    try:
        url = f"https://pypi.org/pypi/{package_name}/json"
        with urlopen(url) as response:
            data = json.loads(response.read().decode())
            return data["info"]["version"]
    except HTTPError as e:
        if e.code == 404:
            # Package not found - this is the first release
            return None
        else:
            raise
    except Exception as e:
        print(f"Error fetching version from PyPI: {e}", file=sys.stderr)
        return None


def parse_version(version_string: str) -> tuple[int, int, int]:
    """
    Parse a semantic version string into major, minor, patch components.

    Args:
        version_string (str): Version string like "1.2.3"

    Returns:
        tuple[int, int, int]: (major, minor, patch)
    """
    # Handle various version formats (1.2.3, v1.2.3, 1.2.3-alpha, etc.)
    match = re.match(r"^v?(\d+)\.(\d+)\.(\d+)", version_string)
    if not match:
        raise ValueError(f"Invalid version format: {version_string}")

    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def format_version(major: int, minor: int, patch: int) -> str:
    """
    Format version components into a semantic version string.

    Args:
        major (int): Major version number
        minor (int): Minor version number
        patch (int): Patch version number

    Returns:
        str: Formatted version string like "1.2.3"
    """
    return f"{major}.{minor}.{patch}"


def calculate_next_version(package_name: str, target_major: int, target_minor: int) -> str:
    """
    Calculate the next version based on PyPI and target major/minor versions.

    Args:
        package_name (str): Package name on PyPI
        target_major (int): Desired major version
        target_minor (int): Desired minor version

    Returns:
        str: Next version string
    """
    latest_version = get_latest_version_from_pypi(package_name)

    if latest_version is None:
        # First release
        return format_version(target_major, target_minor, 1)

    try:
        current_major, current_minor, current_patch = parse_version(latest_version)
    except ValueError as e:
        print(f"Warning: Could not parse current version '{latest_version}': {e}", file=sys.stderr)
        # Default to first release for target major.minor
        return format_version(target_major, target_minor, 1)

    # Determine next version based on target major/minor vs current
    if target_major > current_major or (
        target_major == current_major and target_minor > current_minor
    ):
        # New major or minor version - start patch at 1
        next_patch = 1
    elif target_major == current_major and target_minor == current_minor:
        # Same major.minor - increment patch
        next_patch = current_patch + 1
    else:
        # Target is older than current - this is unusual but we'll start at 1
        print(
            f"Warning: Target version {target_major}.{target_minor} is older than current {current_major}.{current_minor}",
            file=sys.stderr,
        )
        next_patch = 1

    return format_version(target_major, target_minor, next_patch)


def main():
    """Main entry point for the version manager script."""
    if len(sys.argv) != 4:
        print("Usage: python version_manager.py <package_name> <major> <minor>", file=sys.stderr)
        print("Example: python version_manager.py ado-mcp-raboley 0 0", file=sys.stderr)
        sys.exit(1)

    package_name = sys.argv[1]
    try:
        target_major = int(sys.argv[2])
        target_minor = int(sys.argv[3])
    except ValueError:
        print("Error: Major and minor versions must be integers", file=sys.stderr)
        sys.exit(1)

    if target_major < 0 or target_minor < 0:
        print("Error: Major and minor versions must be non-negative", file=sys.stderr)
        sys.exit(1)

    try:
        next_version = calculate_next_version(package_name, target_major, target_minor)
        print(next_version)
    except Exception as e:
        print(f"Error calculating next version: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
