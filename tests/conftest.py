"""Pytest configuration with test ordering based on duration."""

import json

import pytest


def pytest_addoption(parser):
    """Add command line options for test ordering."""
    parser.addoption(
        "--slowest-first",
        action="store_true",
        default=False,
        help="Run slowest tests first based on previous run durations",
    )
    parser.addoption(
        "--mark-slow-threshold",
        type=float,
        default=5.0,
        help="Threshold in seconds to mark tests as slow (default: 5.0)",
    )


def pytest_collection_modifyitems(config, items):
    """Reorder tests based on previous run durations if --slowest-first is used."""
    if not config.getoption("--slowest-first"):
        return

    # Try to load test durations from cache
    cache_dir = config.cache._cachedir
    duration_file = cache_dir / "test_durations.json"

    durations = {}
    if duration_file.exists():
        try:
            with open(duration_file) as f:
                durations = json.load(f)
        except (OSError, json.JSONDecodeError):
            pass

    # Sort items by duration (slowest first)
    def get_duration(item):
        # Get the test node ID
        node_id = item.nodeid
        # Return the cached duration or 0 if not found
        return durations.get(node_id, 0.0)

    # Sort items in descending order by duration (slowest first)
    items.sort(key=get_duration, reverse=True)

    # Optionally add markers for slow tests
    threshold = config.getoption("--mark-slow-threshold")
    for item in items:
        duration = get_duration(item)
        if duration > threshold:
            item.add_marker(pytest.mark.slow)


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Save test durations to cache after test run."""
    if not hasattr(terminalreporter, "stats"):
        return

    # Collect duration data
    durations = {}

    # Get all test reports
    for outcome in ["passed", "failed", "skipped"]:
        reports = terminalreporter.stats.get(outcome, [])
        for report in reports:
            if hasattr(report, "duration") and report.when == "call":
                durations[report.nodeid] = report.duration

    # Save to cache
    if durations:
        cache_dir = config.cache._cachedir
        duration_file = cache_dir / "test_durations.json"

        # Merge with existing durations
        existing_durations = {}
        if duration_file.exists():
            try:
                with open(duration_file) as f:
                    existing_durations = json.load(f)
            except (OSError, json.JSONDecodeError):
                pass

        # Update with new durations
        existing_durations.update(durations)

        # Write back to file
        try:
            duration_file.parent.mkdir(parents=True, exist_ok=True)
            with open(duration_file, "w") as f:
                json.dump(existing_durations, f, indent=2)
        except OSError:
            pass


@pytest.fixture
def show_test_info(request):
    """Fixture to display test execution order and timing info."""
    test_name = request.node.name
    # Get cached duration if available
    cache_dir = request.config.cache._cachedir
    duration_file = cache_dir / "test_durations.json"

    if duration_file.exists():
        try:
            with open(duration_file) as f:
                durations = json.load(f)
                cached_duration = durations.get(request.node.nodeid, 0.0)
                if cached_duration > 0:
                    print(f"\n[Test Order] {test_name} - Previous duration: {cached_duration:.2f}s")
        except:
            pass

    yield
