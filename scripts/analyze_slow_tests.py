#!/usr/bin/env python3
"""Analyze test durations from pytest cache."""

import json
from pathlib import Path


def main():
    # Load test durations
    cache_file = Path(".pytest_cache/test_durations.json")

    if not cache_file.exists():
        print("No test duration cache found. Run tests first to generate duration data.")
        return

    with open(cache_file, "r") as f:
        durations = json.load(f)

    # Sort by duration (slowest first)
    sorted_tests = sorted(durations.items(), key=lambda x: x[1], reverse=True)

    # Print summary
    print(f"Total tests with duration data: {len(durations)}")
    print(f"\nTop 20 slowest tests:")
    print("-" * 80)

    total_time = sum(durations.values())
    slow_cutoff = 5.0  # seconds

    for i, (test_name, duration) in enumerate(sorted_tests[:20]):
        percentage = (duration / total_time) * 100
        test_short = test_name.split("::")[-1] if "::" in test_name else test_name
        print(f"{i + 1:2d}. {duration:7.2f}s ({percentage:5.1f}%) - {test_short[:60]}")

    # Statistics
    print("\n" + "-" * 80)
    slow_tests = [t for t in sorted_tests if t[1] > slow_cutoff]
    print(f"\nTests slower than {slow_cutoff}s: {len(slow_tests)}")
    print(f"Total test time: {total_time:.2f}s")
    print(f"Average test time: {total_time / len(durations):.2f}s")

    # Show time distribution
    print("\nTime distribution:")
    buckets = [0.1, 0.5, 1.0, 5.0, 10.0, float("inf")]
    bucket_names = ["<0.1s", "0.1-0.5s", "0.5-1s", "1-5s", "5-10s", ">10s"]
    bucket_counts = [0] * len(buckets)

    for _, duration in sorted_tests:
        for i, threshold in enumerate(buckets):
            if duration <= threshold:
                bucket_counts[i] += 1
                break

    for name, count in zip(bucket_names, bucket_counts):
        print(f"  {name:10s}: {count:4d} tests")


if __name__ == "__main__":
    main()
