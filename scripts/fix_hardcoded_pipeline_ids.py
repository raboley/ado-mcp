#!/usr/bin/env python3
"""
Fix remaining hardcoded pipeline IDs in test files.

This script identifies and fixes hardcoded pipeline IDs that were missed in the previous conversion.
"""

import logging
import re
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fix_hardcoded_pipeline_ids():
    """Find and fix hardcoded pipeline IDs in test files."""

    # Base directory for tests
    tests_dir = Path("/Users/russellboley/PycharmProjects/ado-mcp/tests")

    # Pattern to find hardcoded pipeline IDs (lines like `parameterized_pipeline_id = 75`)
    hardcoded_id_pattern = re.compile(r"(\s*)([a-zA-Z_]+_pipeline_id)\s*=\s*(\d+)")

    files_with_hardcoded_ids = []

    # Search through all Python test files
    for test_file in tests_dir.rglob("*.py"):
        if test_file.name.startswith("test_"):
            try:
                content = test_file.read_text()

                # Check if file has hardcoded pipeline IDs
                matches = hardcoded_id_pattern.findall(content)
                if matches:
                    files_with_hardcoded_ids.append((test_file, matches))
                    logger.info(f"Found hardcoded IDs in {test_file}: {matches}")
            except Exception as e:
                logger.error(f"Error reading {test_file}: {e}")

    # Fix each file
    for test_file, matches in files_with_hardcoded_ids:
        try:
            content = test_file.read_text()
            original_content = content

            # Replace hardcoded IDs with dynamic lookups
            for indent, var_name, pipeline_id in matches:
                # Map variable names to pipeline names
                pipeline_name_mapping = {
                    "parameterized_pipeline_id": "preview-test-parameterized",
                    "github_resources_pipeline_id": "github-resources-test-stable",
                    "preview_pipeline_id": "preview-test-valid",
                    "basic_pipeline_id": "test_run_and_get_pipeline_run_details",
                    "complex_pipeline_id": "slow.log-test-complex",
                    "failing_pipeline_id": "log-test-failing",
                    "runtime_variables_pipeline_id": "runtime-variables-test",
                }

                pipeline_name = pipeline_name_mapping.get(var_name, "unknown-pipeline")

                # Replace the hardcoded assignment with dynamic lookup
                old_line = f"{indent}{var_name} = {pipeline_id}"
                new_line = f'{indent}{var_name} = await get_pipeline_id_by_name(mcp_client, "{pipeline_name}")'

                content = content.replace(old_line, new_line)
                logger.info(f"Replaced '{old_line}' with '{new_line}' in {test_file}")

            # Only write if content changed
            if content != original_content:
                test_file.write_text(content)
                logger.info(f"Updated {test_file}")

        except Exception as e:
            logger.error(f"Error fixing {test_file}: {e}")


if __name__ == "__main__":
    fix_hardcoded_pipeline_ids()
