"""Fleet canary checker — verifies polyformalism across ALL repos.

Runs each `quilt-canon-*` tool's canary.py and verifies they all produce
the same hash (0x24a555471370b18d). This is the meta-canary: if ANY tool
in the fleet drifts, this catches it.

Why this matters:
- Polyformalism is a bedrock doctrine: same computation, multiple substrates
- A drift means a tool broke its byte-exact parity with the others
- This is the substrate walker canon's version of a regression test
"""
import importlib.util
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional


EXPECTED_CANARY = "0x24a555471370b18d"
FLEET_DIR = Path("/workspace/repos")


def _find_canary_file(repo_dir: Path) -> Optional[Path]:
    """Find a canary.py in a repo. Prefer top-level canary.py."""
    candidates = [
        repo_dir / "canary.py",
    ]
    candidates.extend(repo_dir.glob("**/canary.py"))

    if candidates[0].exists():
        return candidates[0]
    for c in candidates[1:]:
        if c.exists():
            return c
    return None


def _import_canary_module(repo_dir: Path):
    """Import a repo's canary module dynamically."""
    path = _find_canary_file(repo_dir)
    if path is None:
        return None, None
    spec = importlib.util.spec_from_file_location(f"{repo_dir.name}_canary", str(path))
    if spec is None:
        return {"_error": "spec failed"}, path
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
        return mod, path
    except Exception as e:
        return {"_error": str(e)}, path


def _check_via_subprocess(repo_dir: Path) -> Optional[str]:
    """Fallback: run canary.py as subprocess and capture stdout."""
    path = _find_canary_file(repo_dir)
    if path is None:
        return None
    try:
        result = subprocess.run(
            [sys.executable, str(path)],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(repo_dir),
        )
        if result.returncode == 0:
            match = re.search(r"0x[0-9a-f]{16}", result.stdout)
            if match:
                return match.group(0)
        return None
    except Exception:
        return None


def check_one_repo(repo_dir: Path) -> Dict:
    """Check a single repo's canary."""
    name = repo_dir.name
    result = {
        "repo": name,
        "expected": EXPECTED_CANARY,
    }
    path = _find_canary_file(repo_dir)
    if path is None:
        result["status"] = "no_canary"
        return result
    result["canary_path"] = str(path)

    mod, _ = _import_canary_module(repo_dir)
    actual = None

    if mod is not None and not (isinstance(mod, dict) and "_error" in mod):
        if hasattr(mod, "canary"):
            try:
                actual = mod.canary()
            except Exception as e:
                result["call_error"] = f"canary() failed: {e}"
        if actual is None and hasattr(mod, "main"):
            try:
                import io
                from contextlib import redirect_stdout
                buf = io.StringIO()
                with redirect_stdout(buf):
                    mod.main()
                output = buf.getvalue()
                match = re.search(r"0x[0-9a-f]{16}", output)
                if match:
                    actual = match.group(0)
            except Exception as e:
                result["call_error"] = f"main() failed: {e}"

    if actual is None:
        actual = _check_via_subprocess(repo_dir)

    if actual is None:
        result["status"] = "call_error"
        return result

    result["actual"] = actual
    if actual == EXPECTED_CANARY:
        result["status"] = "pass"
    else:
        result["status"] = "drift"
    return result


def check_fleet(repos_dir: Path = FLEET_DIR, only: Optional[List[str]] = None) -> List[Dict]:
    """Check all repos in the fleet."""
    if not repos_dir.exists():
        return []

    results = []
    for repo_dir in sorted(repos_dir.iterdir()):
        if not repo_dir.is_dir():
            continue
        if only and repo_dir.name not in only:
            continue
        if _find_canary_file(repo_dir) is not None:
            results.append(check_one_repo(repo_dir))
    return results


def fleet_stats(results: List[Dict]) -> Dict:
    """Aggregate stats from check results."""
    total = len(results)
    passing = sum(1 for r in results if r.get("status") == "pass")
    drifting = sum(1 for r in results if r.get("status") == "drift")
    no_canary = sum(1 for r in results if r.get("status") == "no_canary")
    errors = sum(1 for r in results if r.get("status") in ("import_error", "call_error"))

    return {
        "total": total,
        "passing": passing,
        "drifting": drifting,
        "no_canary": no_canary,
        "errors": errors,
        "pass_rate": (passing / total * 100) if total > 0 else 0,
        "polyformal": passing == total,
    }


def fleet_canary_hash() -> str:
    """Compute a single hash representing the fleet's overall state."""
    import hashlib
    results = check_fleet()
    state = "|".join(f"{r['repo']}:{r.get('status', '?')}" for r in results)
    return "fleet_" + hashlib.sha256(state.encode()).hexdigest()[:16]
