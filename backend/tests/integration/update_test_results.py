#!/usr/bin/env python
"""Update TEST_RESULTS.md with aggregate benchmark statistics.

This script runs T046 and T047 benchmarks and consolidates results into
a single TEST_RESULTS.md with JSON export for CI/CD integration.
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime


def run_benchmark(script_path: Path) -> dict:
    """Run a benchmark script and return results."""
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=600,
        )
        return {"success": result.returncode == 0, "output": result.stdout}
    except subprocess.TimeoutExpired:
        return {"success": False, "output": "Benchmark timeout"}
    except Exception as e:
        return {"success": False, "output": f"Error: {e}"}


def update_test_results() -> int:
    """Run all benchmarks and update TEST_RESULTS.md."""
    scripts_dir = Path(__file__).parent
    backend_dir = scripts_dir.parent / "backend"
    results_file = backend_dir / "TEST_RESULTS.md"

    print("=== Updating TEST_RESULTS.md ===\n")

    # Run CLI benchmarks
    print("Running CLI YouTube benchmarks...")
    cli_result = run_benchmark(scripts_dir / "run_cli_youtube_benchmarks.py")
    print(f"  CLI Status: {'✓ Pass' if cli_result['success'] else '✗ Fail'}\n")

    # Run REST benchmarks
    print("Running REST social media benchmarks...")
    rest_result = run_benchmark(scripts_dir / "run_rest_social_benchmarks.py")
    print(f"  REST Status: {'✓ Pass' if rest_result['success'] else '✗ Fail'}\n")

    # Aggregate results
    aggregate = {
        "timestamp": datetime.now().isoformat(),
        "cli_youtube_pass": cli_result["success"],
        "rest_social_pass": rest_result["success"],
        "overall_pass": cli_result["success"] and rest_result["success"],
        "benchmark_results": {
            "cli_youtube": {
                "status": "PASS" if cli_result["success"] else "FAIL",
                "output": cli_result["output"][:500],  # First 500 chars
            },
            "rest_social": {
                "status": "PASS" if rest_result["success"] else "FAIL",
                "output": rest_result["output"][:500],
            },
        },
    }

    # Write JSON export
    json_file = backend_dir / "test_results.json"
    with open(json_file, "w") as f:
        json.dump(aggregate, f, indent=2)
    print(f"JSON export: {json_file}")

    # Update markdown with aggregate summary
    if results_file.exists():
        content = results_file.read_text()
        if "## Test Summary" not in content:
            summary = f"""
## Test Summary

**Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

### Benchmark Status

- **CLI YouTube (SC-001)**: {'✓ PASS' if aggregate['cli_youtube_pass'] else '✗ FAIL'}
- **REST Social Media (SC-002)**: {'✓ PASS' if aggregate['rest_social_pass'] else '✗ FAIL'}
- **Overall**: {'✓ PASS' if aggregate['overall_pass'] else '✗ FAIL'}

"""
            results_file.write_text(content + summary)

    print(f"\nUpdated: {results_file}")
    return 0 if aggregate["overall_pass"] else 1


if __name__ == "__main__":
    exit_code = update_test_results()
    sys.exit(exit_code)
