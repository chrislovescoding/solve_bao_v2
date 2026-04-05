# Bao la Kujifunza Strong Solver

Research code for strongly solving Bao la Kujifunza with:

- a Python reference engine,
- a Rust native core for packed-state enumeration and slice solving,
- reproducible logs, rules, and pipeline tooling.

## Repository Scope

This repository tracks source code, tests, rules/docs, and pipeline scripts.
Generated build products and large research artifacts are intentionally not
committed; they are written under `artifacts/` and `target/`.

## Layout

- `bao/`: Python reference engine, shard readers, SCC solver, solution-shard helpers
- `native/bao_solver_core/`: Rust native core and native export/benchmark binaries
- `tools/`: corpus builders, exporters, verifiers, and depth-pipeline runners
- `tests/`: Python test suite
- `docs/`: rules, shard format notes, and pipeline notes
- `research_log.md`: running scientific notebook
- `implementation_checklist.md`: engineering checklist

## Local Setup

Python:

```powershell
python -m unittest discover -s tests -v
```

Rust:

```powershell
cargo test
```

## Typical Workflows

Depth slice export and SCC solve:

```powershell
python tools\run_depth_pipeline.py `
  --depth 9 `
  --output-dir artifacts\pipeline\depth9 `
  --resume
```

Fast remote run without JSONL export:

```powershell
python tools\run_depth_pipeline.py `
  --depth 10 `
  --output-dir artifacts\pipeline\depth10_fast `
  --skip-jsonl `
  --skip-census `
  --resume
```

## Current Status

- Rules baseline: `docs/rulespec_v1.md`
- Native slice solving currently reaches verified SCC-based depth-9 slice artifacts
- The full game is not yet strongly solved

## Notes

- See `research_log.md` for the lab notebook and dated results.
- See `docs/native_shard_formats.md` for binary state/edge/solution formats.
- See `docs/depth_pipeline.md` for the resumable deeper-run pipeline.
