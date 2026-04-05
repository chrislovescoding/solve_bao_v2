# Bao la Kujifunza Implementation Checklist

This checklist translates the current source-audited working rules in
`formal_rules.md` into engineering work items for the reference engine and
future exact solver.

## Rule-Freezing Notes

- [x] Replace `rules.md` as the working authority with `formal_rules.md`.
- [x] Confirm a critical sowing distinction from the primary source:
  ordinary mtaji sowing continues from the next pit after the chosen start
  pit, while capture resowing starts in the chosen kichwa itself.
- [ ] Freeze a publication-ready adjudication rule for repeated positions
  across turns.
- [ ] Decide whether every self-emptying front-row move is illegal or merely a
  legal move to immediate loss when the rules do not state an explicit
  prohibition.

Primary-source note:

- Donkers, Appendix C, rule 1.6 says endelea restarts at the next pit.
- Donkers, Appendix C notation note says mtaji direction is the hand movement
  after picking up stones, which is consistent with next-pit ordinary sowing.

Reference:

- [Donkers thesis PDF](https://project.dke.maastrichtuniversity.nl/games/files/phd/Donkers_thesis.pdf)

## State Representation

- [x] Fix an absolute 32-pit coordinate system.
- [x] Represent side to move explicitly.
- [x] Enforce seed conservation at the state object boundary.
- [x] Add helpers for rows, columns, opposites, kichwa, and kimbi.
- [x] Add symmetry transforms and a canonical key.
- [ ] Document the canonical-state proof obligations for the solver paper.

## Move Generation

- [x] Enumerate pseudo-legal starts from pits with at least 2 stones.
- [x] Detect capture starts using first-sowing simulation only.
- [x] Enforce the `>= 16` opening-pit rule for mtaji eligibility.
- [x] Enforce mandatory capture.
- [x] Enforce takasa front-row priority.
- [x] Enforce the explicit lone-kichwa takasa direction restriction.
- [x] Filter infinite moves from the legal move list.
- [ ] Decide and document how legal-move generation should treat
  self-emptying capture attempts, if any exist in the reachable game graph.

## Move Execution

- [x] Distinguish ordinary sowing from capture resowing.
- [x] Keep direction fixed within a sowing.
- [x] Continue relay sowing from the next pit after a non-capturing landing.
- [x] Trigger captures only in mtaji moves.
- [x] Sustain direction on non-kimbi captures.
- [x] Force left/right kichwa on kimbi captures.
- [x] Stop a move when the last seed lands in an empty pit.
- [x] Stop immediately if a front row becomes empty during the move.
- [x] Detect within-turn infinite moves exactly by repeated pending-sowing
  states.
- [x] Add structured traces suitable for later proof logging and publication
  examples.

## Validation

- [x] Add unit tests for sow-path semantics.
- [x] Add unit tests for mandatory capture.
- [x] Add unit tests for the `>= 16` rule.
- [x] Add unit tests for takasa front-row priority.
- [x] Add unit tests for the lone-kichwa takasa restriction.
- [x] Add unit tests for symmetry canonicalization.
- [x] Add regression tests for relay-driven secondary captures.
- [ ] Add tests for explicit infinite-move examples from the literature.
- [ ] Add randomized differential tests against a second implementation.
- [x] Add a first fixed native correctness corpus for cross-language state-key
  validation.
- [x] Add a first cross-language corpus check for native legal-move sets.
- [x] Add a first cross-language corpus check for full successor results.

## Solver Preparation

- [x] Provide a minimal, exact reference-engine interface.
- [x] Add stable state serialization for artifact files.
- [x] Add per-position statistics hooks for branching factor and move length.
- [x] Add a first native benchmark harness for state-key packing and
  unpacking.
- [x] Start the native move-generation port with regression-tested legal-move
  generation and move application.
- [x] Add a native shallow-census tool that reproduces the reference shallow
  reachability profile.
- [x] Add a native move-generation benchmark harness over a reachable-state
  corpus.
- [x] Add a first canonical frontier export with checksum manifest.
- [x] Add a first canonical graph-slice export with separate state and edge
  shards plus manifests.
- [x] Add a first compact binary state/edge shard format with verification
  against JSONL source shards.
- [x] Move binary shard writing into Rust with fixed shard headers and native
  verification against JSONL graph slices.
- [x] Add a grouped-adjacency native edge shard and phase-timed native export
  summary.
- [x] Add native shard header inspection tooling and format notes.
- [x] Reduce native export terminal-annotation cost with early-exit legal-move
  detection and expanded-state reuse.
- [x] Add a direct adjacency-shard query tool for local-ID successor access.
- [x] Add canonical-state-key lookup over the sorted native state shard for
  oracle-style slice queries.
- [x] Add bulk native shard decoders for efficient Python-side solver tools.
- [x] Add a first slice-local partial solver over the adjacency representation.
- [x] Add tablebase-friendly terminal annotations to the native state shard.
- [x] Add a first fixed-width `SolveRecord`-style partial solution shard plus
  verifier.
- [x] Add a query tool for looking up partial solution records by local ID or
  canonical state key.
- [x] Add an SCC-based slice solver over the native adjacency representation.
- [x] Add a resumable depth-pipeline runner suitable for longer GCP slice jobs.
- [ ] Add true distributed GCP sharding/orchestration wrappers for multi-VM
  enumeration and solving.
