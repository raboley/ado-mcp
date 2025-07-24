#!/usr/bin/env python3
"""
Quick fix script to repair broken imports from the conversion process.
"""

import os
import re


def fix_file_imports(file_path):
    """Fix broken imports in a single file."""
    print(f"Fixing {file_path}...")

    with open(file_path) as f:
        content = f.read()

    original_content = content

    # Fix broken import os
    content = re.sub(r"^i$\n", "import os\n", content, flags=re.MULTILINE)
    content = re.sub(r"^mport os$", "import os", content, flags=re.MULTILINE)

    # Fix broken test_config imports
    content = re.sub(r"get_project_, get_project_namename", "get_project_name", content)
    content = re.sub(r"get_basic_pipeli, get_project_namene_id", "get_project_name", content)
    content = re.sub(
        r"get_project_name, get_.*_pipeline_id[^,]*(?:, )?", "get_project_name", content
    )
    content = re.sub(r"get_.*_pipeline_id, get_project_name", "get_project_name", content)

    # Clean up any remaining pipeline ID function references in imports
    content = re.sub(r", get_.*_pipeline_id", "", content)
    content = re.sub(r"get_.*_pipeline_id, ", "", content)

    # Remove duplicate helper function definitions (keep the first one)
    helper_pattern = r'async def get_pipeline_id_by_name\(mcp_client: Client, pipeline_name: str\) -> int:.*?return pipeline_info\["pipeline"\]\["id"\]'
    matches = list(re.finditer(helper_pattern, content, re.DOTALL))
    if len(matches) > 1:
        # Remove all but the first match
        for match in reversed(matches[1:]):
            content = content[: match.start()] + content[match.end() :]

    # Remove orphaned function fragments
    content = re.sub(
        r"^async def get_pipeline_id_by_name.*?^$", "", content, flags=re.MULTILINE | re.DOTALL
    )

    # Clean up multiple blank lines
    content = re.sub(r"\n\n\n+", "\n\n", content)

    if content != original_content:
        with open(file_path, "w") as f:
            f.write(content)
        print(f"  ✅ Fixed {file_path}")
    else:
        print(f"  ⏭️  No fixes needed for {file_path}")


def main():
    """Fix all Python test files."""
    print("🔧 Fixing broken imports from conversion...")

    # Find all Python test files
    test_files = []
    for root, _dirs, files in os.walk("tests"):
        for file in files:
            if file.endswith(".py") and not file.startswith("__"):
                test_files.append(os.path.join(root, file))

    print(f"Found {len(test_files)} test files to check")

    for file_path in test_files:
        try:
            fix_file_imports(file_path)
        except Exception as e:
            print(f"  ❌ Error fixing {file_path}: {e}")

    print("\n🎉 Import fixes complete!")


if __name__ == "__main__":
    main()
