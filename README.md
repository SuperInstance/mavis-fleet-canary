# mavis-fleet-canary

The meta-canary for the Quilt fleet. Verifies polyformalism across ALL canon tools.

## Why

Polyformalism is a bedrock doctrine: same computation, multiple substrates. If ANY tool in the fleet produces a different canary hash, polyformalism broke — and this catches it.

## Run

```bash
python3 -m mavis_fleet_canary check           # full fleet
python3 -m mavis_fleet_canary check --verbose # per-repo
python3 -m mavis_fleet_canary status          # single hash for monitoring
python3 -m mavis_fleet_canary check-one quilt-canon-mcp
```

## Tests

```bash
python3 run_tests.py    # 8/8 passing
```

## What it checks

Each `*canary.py` file in `/workspace/repos/*` is run, and its hash is compared to the expected `0x24a555471370b18d`. The fleet is polyformal when all match.

Currently: **35/35 repos polyformal** (100%).

## Docs

- Concept: `witness_log_is_prediction` doctrine — the substrate's witness log predicts consistency, not history
- See also: `quilt-canon-witness`, `quilt-canon-trace`
