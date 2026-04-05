# Optimization Harness

This repository now has deterministic optimization harnesses for the current
native hot paths:

- `export_binary`
- `solve_slice_dag`

The driver is:

- [run_optimization_harness.py](C:/Users/Chris/Desktop/solve_bao_v2/tools/run_optimization_harness.py)

The harness is designed for iterative agent loops:

1. build the release binary outside measured trials,
2. run fixed correctness gates,
3. run repeated timed trials,
4. capture Linux peak RSS when `/usr/bin/time -v` is available,
5. write a machine-readable JSON report.

## Correctness Model

Correctness expectations live in:

- [hot_path_expectations.json](C:/Users/Chris/Desktop/solve_bao_v2/benchmarks/hot_path_expectations.json)

For the current hot paths, correctness gates compare:

- exact summary subsets, and
- exact SHA-256 hashes of deterministic binary outputs.

Current deterministic correctness depths:

- `6`
- `9`

These are intended to reject performance-only edits that silently change solver
behavior or artifact layout.

## Example Commands

Export benchmark:

```powershell
python tools\run_optimization_harness.py export_binary --benchmark-depth 9 --trials 3
```

Native DAG solve benchmark:

```powershell
python tools\run_optimization_harness.py solve_slice_dag --benchmark-depth 9 --trials 5
```

Using a larger prebuilt benchmark slice on GCP:

```powershell
python tools\run_optimization_harness.py solve_slice_dag --trials 5 --benchmark-depth 11 --benchmark-state-binary artifacts\pipeline\depth11_fast\shards\native_state_slice_depth11.bin --benchmark-adjacency-binary artifacts\pipeline\depth11_fast\shards\native_adjacency_slice_depth11.bin --benchmark-graph-summary artifacts\pipeline\depth11_fast\shards\native_graph_slice_depth11.summary.json
```

## Intended Agent-Loop Usage

The optimization loop should:

1. change only the target function or representation,
2. run the corresponding harness,
3. reject the change immediately if any correctness gate fails,
4. compare median wall time and peak RSS to the previous accepted report,
5. keep the change only if it clears the promotion rule.

Current promotion rule:

- correctness gates must pass,
- output must remain deterministic,
- require at least `20%` stage speedup or `10%` end-to-end speedup.
