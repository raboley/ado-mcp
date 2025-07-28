#!/usr/bin/env python3
"""
Script to identify and fix potentially flaky tests in the ado-mcp project.

This script looks for patterns that are prone to flakiness due to:
- Cache inconsistency
- API propagation delays
- Parallel test execution issues
- Azure DevOps eventual consistency

Usage:
    python fix_flaky_tests.py --identify  # Just identify potential issues
    python fix_flaky_tests.py --fix       # Apply fixes
"""

import argparse
import os
import re
from pathlib import Path

# Patterns that indicate potential flakiness
FLAKY_PATTERNS = [
    # Tool calls that depend on cached data
    (
        r'await\s+mcp_client\.call_tool\s*\(\s*["\']run_pipeline_by_name["\']',
        "run_pipeline_by_name without retry",
    ),
    (
        r'await\s+mcp_client\.call_tool\s*\(\s*["\']find_pipeline_by_name["\']',
        "find_pipeline_by_name without retry",
    ),
    (
        r'await\s+mcp_client\.call_tool\s*\(\s*["\']get_pipeline_failure_summary_by_name["\']',
        "failure_summary_by_name without retry",
    ),
    (
        r'await\s+mcp_client\.call_tool\s*\(\s*["\']watch_pipeline_by_name["\']',
        "watch_pipeline_by_name without retry",
    ),
    (
        r'await\s+mcp_client\.call_tool\s*\(\s*["\']extract_pipeline_run_data_by_name["\']',
        "extract_data_by_name without retry",
    ),
    # Direct assertions on API responses without waiting
    (r"assert\s+\w+.*in.*pipeline.*list", "Direct assertion on pipeline list without wait"),
    (r"assert\s+pipeline.*should.*appear", "Direct assertion expecting pipeline to appear"),
    (r"assert\s+\w+.*should.*exist", "Direct assertion expecting existence"),
    # Create/delete patterns without retry
    (r"create_pipeline.*\n.*assert.*in", "Create pipeline followed by immediate assertion"),
    (r"delete_pipeline.*\n.*assert.*not.*in", "Delete pipeline followed by immediate assertion"),
]

# Files to exclude from analysis
EXCLUDE_FILES = [
    "fix_flaky_tests.py",
    "retry_helpers.py",
    "__pycache__",
    ".pyc",
]


def find_test_files(test_dir: str = "tests") -> list[Path]:
    """Find all Python test files."""
    test_files = []
    for root, dirs, files in os.walk(test_dir):
        # Skip __pycache__ directories
        dirs[:] = [d for d in dirs if d != "__pycache__"]

        for file in files:
            if file.endswith(".py") and not any(exclude in file for exclude in EXCLUDE_FILES):
                test_files.append(Path(root) / file)

    return test_files


def analyze_file(file_path: Path) -> list[tuple[int, str, str]]:
    """Analyze a file for flaky patterns."""
    issues = []

    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
            lines = content.split("\n")
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return issues

    for pattern, description in FLAKY_PATTERNS:
        for match in re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE):
            # Find line number
            line_num = content[: match.start()].count("\n") + 1
            line_content = lines[line_num - 1].strip()
            issues.append((line_num, description, line_content))

    return issues


def generate_fix_suggestions(file_path: Path, issues: list[tuple[int, str, str]]) -> list[str]:
    """Generate fix suggestions for identified issues."""
    suggestions = []

    for line_num, description, line_content in issues:
        if "run_pipeline_by_name without retry" in description:
            suggestions.append(f"""
Line {line_num}: {line_content}
Fix: Wrap with retry_with_cache_invalidation:
    result = await retry_with_cache_invalidation(
        mcp_client,
        "run_pipeline_by_name",
        {{"project_name": PROJECT_NAME, "pipeline_name": PIPELINE_NAME}},
        max_retries=3,
        retry_delay=1
    )
""")

        elif "Direct assertion" in description:
            suggestions.append(f"""
Line {line_num}: {line_content}
Fix: Add wait mechanism or use retry pattern for eventual consistency
""")

        elif "Create pipeline followed by immediate assertion" in description:
            suggestions.append(f"""
Line {line_num}: {line_content}
Fix: Add wait_for_pipeline_creation() after create_pipeline
""")

        elif "Delete pipeline followed by immediate assertion" in description:
            suggestions.append(f"""
Line {line_num}: {line_content}
Fix: Add wait_for_pipeline_deletion() after delete_pipeline
""")

    return suggestions


def main():
    parser = argparse.ArgumentParser(description="Identify and fix flaky tests")
    parser.add_argument("--identify", action="store_true", help="Only identify potential issues")
    parser.add_argument("--fix", action="store_true", help="Apply fixes (not implemented yet)")
    parser.add_argument("--test-dir", default="tests", help="Test directory to analyze")

    args = parser.parse_args()

    if not args.identify and not args.fix:
        args.identify = True  # Default to identify mode

    test_files = find_test_files(args.test_dir)
    print(f"Analyzing {len(test_files)} test files...")

    total_issues = 0
    files_with_issues = 0

    for file_path in test_files:
        issues = analyze_file(file_path)

        if issues:
            files_with_issues += 1
            total_issues += len(issues)
            print(f"\n{'=' * 60}")
            print(f"File: {file_path}")
            print(f"{'=' * 60}")

            if args.identify:
                for line_num, description, line_content in issues:
                    print(f"  Line {line_num}: {description}")
                    print(f"    Code: {line_content}")

                # Generate fix suggestions
                suggestions = generate_fix_suggestions(file_path, issues)
                if suggestions:
                    print("\n  Fix suggestions:")
                    for suggestion in suggestions:
                        print(f"    {suggestion}")

    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    print(f"Files analyzed: {len(test_files)}")
    print(f"Files with potential issues: {files_with_issues}")
    print(f"Total potential issues: {total_issues}")

    if total_issues > 0:
        print("\nRecommendations:")
        print(
            "1. Add 'from tests.utils.retry_helpers import retry_with_cache_invalidation' to imports"
        )
        print("2. Wrap name-based tool calls with retry_with_cache_invalidation()")
        print("3. Use wait_for_pipeline_creation/deletion for create/delete operations")
        print("4. Consider using retry_pipeline_operation() for complex operations")
        print("\nSee tests/utils/retry_helpers.py for available utilities.")


if __name__ == "__main__":
    main()
