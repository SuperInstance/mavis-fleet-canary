"""Test runner for mavis-fleet-canary (no pytest dep)."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/workspace/repos/mavis-fleet-canary")

from mavis_fleet_canary.canary import canary
from mavis_fleet_canary.checker import (
    check_one_repo,
    check_fleet,
    fleet_stats,
    fleet_canary_hash,
    EXPECTED_CANARY,
)

results = []
failures = []


def test(name, func):
    try:
        func()
        results.append((name, "PASS"))
    except AssertionError as e:
        results.append((name, f"FAIL: {e}"))
        failures.append(name)
    except Exception as e:
        results.append((name, f"ERROR: {type(e).__name__}: {e}"))
        failures.append(name)


def t_canary():
    assert canary() == "0x24a555471370b18d"


def t_expected_value():
    assert EXPECTED_CANARY == "0x24a555471370b18d"


def test_check_real_fleet():
    """Check the real fleet at /workspace/repos."""
    results_list = check_fleet()
    assert len(results_list) >= 5
    stats = fleet_stats(results_list)
    assert stats["total"] == len(results_list)
    assert stats["passing"] > 0


def test_fleet_stats():
    fake = [
        {"repo": "a", "status": "pass"},
        {"repo": "b", "status": "pass"},
        {"repo": "c", "status": "drift"},
    ]
    stats = fleet_stats(fake)
    assert stats["total"] == 3
    assert stats["passing"] == 2
    assert stats["drifting"] == 1
    assert stats["polyformal"] is False


def test_fleet_polyformal_when_all_pass():
    fake = [
        {"repo": "a", "status": "pass"},
        {"repo": "b", "status": "pass"},
    ]
    stats = fleet_stats(fake)
    assert stats["polyformal"] is True


def test_fleet_hash_stable():
    """Same fleet state → same hash."""
    h1 = fleet_canary_hash()
    h2 = fleet_canary_hash()
    assert h1 == h2
    assert h1.startswith("fleet_")


def test_check_fleet_with_only():
    """--only filter works."""
    results_list = check_fleet(only=["quilt-canon-mcp"])
    # Should only check the specified repo (if it exists)
    for r in results_list:
        assert r["repo"] == "quilt-canon-mcp"


def test_check_nonexistent_repo():
    """Checking a non-existent repo returns no_canary status."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        empty_dir = Path(td) / "empty"
        empty_dir.mkdir()
        result = check_one_repo(empty_dir)
        assert result["status"] == "no_canary"


with tempfile.TemporaryDirectory() as td:
    tmp = Path(td)
    test("test_canary", t_canary)
    test("test_expected_value", t_expected_value)
    test("test_check_real_fleet", test_check_real_fleet)
    test("test_fleet_stats", test_fleet_stats)
    test("test_fleet_polyformal_when_all_pass", test_fleet_polyformal_when_all_pass)
    test("test_fleet_hash_stable", test_fleet_hash_stable)
    test("test_check_fleet_with_only", test_check_fleet_with_only)
    test("test_check_nonexistent_repo", lambda: test_check_nonexistent_repo())

print("\n=== mavis-fleet-canary test results ===")
for name, status in results:
    print(f"  {status:60} {name}")

print(f"\n{len(results) - len(failures)}/{len(results)} passed")
if failures:
    sys.exit(1)
