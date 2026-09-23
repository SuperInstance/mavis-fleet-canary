"""CLI for mavis-fleet-canary."""
import argparse
import json
import sys
from pathlib import Path

from .checker import check_one_repo, check_fleet, fleet_stats, fleet_canary_hash, EXPECTED_CANARY, FLEET_DIR


def cmd_check(args):
    """Check all repos in the fleet."""
    results = check_fleet(Path(args.repos_dir) if args.repos_dir else FLEET_DIR,
                          only=args.only.split(",") if args.only else None)
    stats = fleet_stats(results)
    print(f"Fleet canary check ({stats['total']} repos):")
    print(f"  Expected: {EXPECTED_CANARY}")
    print(f"  Passing:  {stats['passing']}")
    print(f"  Drifting: {stats['drifting']}")
    print(f"  Errors:   {stats['errors']}")
    print(f"  No canary: {stats['no_canary']}")
    print(f"  Pass rate: {stats['pass_rate']:.1f}%")
    print(f"  Polyformal: {'✓ YES' if stats['polyformal'] else '✗ NO'}")
    print()

    if args.verbose or not stats["polyformal"]:
        print("Per-repo results:")
        for r in results:
            status = r.get("status", "?")
            actual = r.get("actual", "")
            mark = {
                "pass": "✓",
                "drift": "✗ DRIFT",
                "no_canary": "?",
                "import_error": "!",
                "call_error": "!",
            }.get(status, "?")
            print(f"  {mark:>8} {r['repo']:35s} {status:12s} {actual}")

    if args.json:
        out = {"stats": stats, "results": results, "fleet_hash": fleet_canary_hash()}
        if args.output:
            Path(args.output).write_text(json.dumps(out, indent=1))
            print(f"\n✓ Saved → {args.output}")
        else:
            print(json.dumps(out, indent=2))

    if stats["polyformal"]:
        sys.exit(0)
    else:
        sys.exit(1)


def cmd_status(args):
    """Show just the fleet canary hash (for monitoring)."""
    print(fleet_canary_hash())


def cmd_check_one(args):
    """Check a single repo."""
    repo = Path(args.repo)
    if not repo.is_absolute():
        repo = FLEET_DIR / repo
    result = check_one_repo(repo)
    print(json.dumps(result, indent=2))


def main():
    p = argparse.ArgumentParser(description="mavis-fleet-canary — meta-canary for the Quilt fleet")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_c = sub.add_parser("check", help="Check all repos in the fleet")
    p_c.add_argument("--repos-dir", help="Repos directory (default: /workspace/repos)")
    p_c.add_argument("--only", help="Comma-separated list of repos to check")
    p_c.add_argument("--verbose", "-v", action="store_true")
    p_c.add_argument("--json", action="store_true", help="Output JSON")
    p_c.add_argument("--output", help="Save JSON output to file")
    p_c.set_defaults(func=cmd_check)

    sub.add_parser("status", help="Show fleet canary hash").set_defaults(func=cmd_status)

    p_co = sub.add_parser("check-one", help="Check a single repo")
    p_co.add_argument("repo", help="Path or name of repo")
    p_co.set_defaults(func=cmd_check_one)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
