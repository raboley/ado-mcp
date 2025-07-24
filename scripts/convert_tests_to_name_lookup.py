#!/usr/bin/env python3
"""
Script to convert tests from using hardcoded pipeline ID functions to name-based MCP lookups.

This script automatically updates test files to:
1. Remove imports of pipeline ID functions from test_config
2. Add the get_pipeline_id_by_name helper function
3. Replace all calls to get_*_pipeline_id() with name-based lookups
"""

import os
import re
import subprocess

# Mapping of old function names to pipeline names
PIPELINE_FUNCTION_MAPPING = {
    "get_basic_pipeline_id": "test_run_and_get_pipeline_run_details",
    "get_complex_pipeline_id": "slow.log-test-complex",
    "get_failing_pipeline_id": "log-test-failing",
    "get_parameterized_pipeline_id": "preview-test-parameterized",
    "get_preview_pipeline_id": "preview-test-valid",
    "get_github_resources_pipeline_id": "github-resources-test-stable",
    "get_runtime_variables_pipeline_id": "runtime-variables-test",
}

HELPER_FUNCTION = '''
async def get_pipeline_id_by_name(mcp_client: Client, pipeline_name: str) -> int:
    """Helper function to get pipeline ID by name using MCP tools."""
    project_name = get_project_name()

    result = await mcp_client.call_tool("find_pipeline_by_name", {
        "project_name": project_name,
        "pipeline_name": pipeline_name
    })

    pipeline_info = result.data
    if not pipeline_info or "pipeline" not in pipeline_info:
        raise ValueError(f"Pipeline '{pipeline_name}' not found in project '{project_name}'")

    return pipeline_info["pipeline"]["id"]
'''


def find_test_files_with_pipeline_functions():
    """Find all test files that use the old pipeline ID functions."""
    result = subprocess.run(
        ["grep", "-r", "-l", "get_.*_pipeline_id", "tests/"],
        capture_output=True,
        text=True,
        cwd="/Users/russellboley/PycharmProjects/ado-mcp",
    )

    if result.returncode == 0:
        return result.stdout.strip().split("\n")
    return []


def update_imports(content):
    """Update the imports to remove pipeline ID functions and add get_project_name."""
    # Find the test_config import line
    import_pattern = r"from src\.test_config import ([^\\n]+)"
    import_match = re.search(import_pattern, content)

    if not import_match:
        return content

    import_items = import_match.group(1)

    # Remove all pipeline ID function imports
    for func_name in PIPELINE_FUNCTION_MAPPING.keys():
        import_items = re.sub(f",\\s*{func_name}", "", import_items)
        import_items = re.sub(f"{func_name}\\s*,", "", import_items)
        import_items = re.sub(f"{func_name}", "", import_items)

    # Add get_project_name if not already present
    if "get_project_name" not in import_items:
        import_items = import_items.rstrip(", ") + ", get_project_name"

    # Clean up extra commas and spaces
    import_items = re.sub(r",\\s*,", ",", import_items)
    import_items = re.sub(r"^,\\s*", "", import_items)
    import_items = re.sub(r"\\s*,$", "", import_items)

    new_import = f"from src.test_config import {import_items}"
    return content.replace(import_match.group(0), new_import)


def add_helper_function(content):
    """Add the helper function after the mcp_client fixture."""
    # Look for the mcp_client fixture
    fixture_pattern = r"(@pytest\\.fixture[^}]*?async def mcp_client[^}]*?yield client)"
    fixture_match = re.search(fixture_pattern, content, re.DOTALL)

    if fixture_match:
        # Add the helper function after the fixture
        replacement = fixture_match.group(1) + HELPER_FUNCTION
        return content.replace(fixture_match.group(1), replacement)

    # If no fixture found, add after imports
    import_end = content.find("pytestmark = pytest.mark.asyncio")
    if import_end != -1:
        insert_pos = content.find("\\n\\n", import_end) + 2
        return content[:insert_pos] + HELPER_FUNCTION + content[insert_pos:]

    return content


def replace_function_calls(content):
    """Replace all pipeline ID function calls with name-based lookups."""
    for func_name, pipeline_name in PIPELINE_FUNCTION_MAPPING.items():
        # Replace the function call with name-based lookup
        pattern = f"{func_name}\\(\\)"
        replacement = f'await get_pipeline_id_by_name(mcp_client, "{pipeline_name}")'
        content = re.sub(pattern, replacement, content)

    return content


def update_test_file(file_path):
    """Update a single test file to use name-based lookups."""
    print(f"Updating {file_path}...")

    with open(file_path) as f:
        content = f.read()

    original_content = content

    # Apply transformations
    content = update_imports(content)
    content = add_helper_function(content)
    content = replace_function_calls(content)

    # Only write if content changed
    if content != original_content:
        with open(file_path, "w") as f:
            f.write(content)
        print(f"  ✅ Updated {file_path}")
    else:
        print(f"  ⏭️  No changes needed for {file_path}")


def main():
    """Main conversion script."""
    print("🔄 Converting tests to use name-based pipeline lookups...")
    print()

    # Find files that need updating
    test_files = find_test_files_with_pipeline_functions()

    if not test_files:
        print("No test files found with pipeline ID functions.")
        return

    print(f"Found {len(test_files)} files to update:")
    for file in test_files:
        print(f"  - {file}")
    print()

    # Update each file
    for file_path in test_files:
        if os.path.exists(file_path):
            try:
                update_test_file(file_path)
            except Exception as e:
                print(f"  ❌ Error updating {file_path}: {e}")

    print()
    print("🎉 Conversion complete!")
    print("📝 Next steps:")
    print("  1. Run tests to verify everything works: task test")
    print("  2. Check for any remaining issues in test output")


if __name__ == "__main__":
    main()
