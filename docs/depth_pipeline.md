# Depth Pipeline

This document records the current one-command slice pipeline for deeper native
solve experiments.

The driver is:

- [run_depth_pipeline.py](C:/Users/Chris/Desktop/solve_bao_v2/tools/run_depth_pipeline.py)

It orchestrates:

1. optional shallow census,
2. optional JSONL slice export,
3. native binary slice export,
4. optional binary-vs-JSONL verification,
5. SCC slice solve,
6. solution-shard verification,
7. a pipeline manifest with per-step timings and artifact paths.

The pipeline now streams live step progress and child-script output to stdout,
so long remote jobs no longer sit silently between artifact writes.

For the `solve_scc` stage, the pipeline now prefers a native DAG slice solver
and only falls back to the older Python SCC path if the expanded slice actually
contains cycles.

## Local Example

```powershell
python tools\run_depth_pipeline.py `
  --depth 9 `
  --output-dir artifacts\pipeline\depth9 `
  --resume
```

## Faster Remote Example

This mode is useful for GCP VM jobs where we want binary artifacts and solver
results quickly, without paying the extra JSONL export and verification cost on
every exploratory depth.

```powershell
python tools\run_depth_pipeline.py `
  --depth 9 `
  --output-dir artifacts\pipeline\depth9_fast `
  --skip-jsonl `
  --skip-census `
  --resume
```

## Output Layout

Inside the chosen `--output-dir`, the pipeline writes:

- `shards/`
  - native state shard
  - native edge shard
  - native adjacency shard
  - binary export summary
- `solve/`
  - SCC solve summary
  - solution shard
  - solution manifest
- `analysis/`
  - detailed SCC statistics
- `census/`
  - optional shallow census report
- `pipeline_depth<N>.manifest.json`
  - per-step command log and timing summary

## Current Usage Notes

- For publication-grade runs, keep JSONL export and verification enabled for at
  least representative depths and sampled larger jobs.
- For exploratory remote runs, `--skip-jsonl` is acceptable when the exact same
  code path has already been validated on nearby depths.
- `--resume` is important for long VM jobs because it lets reruns skip completed
  stages after interruption.
