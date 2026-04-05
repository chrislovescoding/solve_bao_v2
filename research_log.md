# Bao la Kujifunza Strong-Solution Research Log

## Project Objective

Determine the exact game-theoretic value of Bao la Kujifunza from the initial
position under a fully specified, publication-ready rule set, and produce
reproducible evidence strong enough to support a game-science publication.

For this project, "strongly solve" means:

- the initial position is assigned its exact value under perfect play;
- optimal play can be produced from every reachable position in the solved
  ruleset, or from a rigorously defined solved state space sufficient to prove
  the initial-position result;
- every claim is backed by auditable code, logged experiments, and independent
  validation.

## Source Baseline

Current formal rule source:

- [rules.md](C:\Users\Chris\Desktop\solve_bao_v2\rules.md)

This file already resolves many important ambiguities using primary sources.
It will serve as the starting ruleset for implementation and later
publication-grade formalization.

## Scientific Working Principles

- Fix the rules before claiming results.
- Log every meaningful decision, experiment, failure, and change in this file.
- Keep solver correctness separate from solver speed.
- Prefer exact proofs, exact counts, and independently checkable artifacts over
  heuristic claims.
- Treat GPUs as optional accelerators for search guidance, not as sources of
  truth.
- Preserve reproducibility: record hardware, commands, parameters, seeds,
  input data, and output artifact locations.

## Immediate Research Risk Register

### R1. The ruleset is not yet fully publication-ready

`rules.md` is already strong, but one point is explicitly marked as a solver
design choice rather than a rule:

- repeated positions across turns are suggested to be treated as draws, or a
  maximum game-length cutoff may be used.

That is not yet acceptable for a journal-grade strong solution. Before any
final claim, we must do one of the following:

1. derive and justify a definitive adjudication rule from primary sources or
   accepted computer-play conventions;
2. define a precise modern computational ruleset and clearly present it as the
   solved game variant;
3. prove that the unresolved case does not affect the claimed result.

### R2. Infinite move handling must be formalized rigorously

`rules.md` follows Donkers/Kronenburg in treating never-ending moves as
illegal. For a publishable solver, we should move from a simple sow-count
threshold toward an exact or strongly justified infinite-move detector whenever
possible.

### R3. State-space size may be extremely large

A full strong solution may require a hybrid approach:

- exact move generator and verifier;
- cycle-aware search;
- symmetry reduction;
- tablebases for tractable subspaces;
- distributed proof search on GCP.

## Master Plan

### Phase 0. Freeze the Formal Game Definition

Goal:
produce a solver-ready and publication-ready specification with no unresolved
adjudication cases.

Deliverables:

- a cleaned formal rules document derived from `rules.md`;
- a written adjudication rule for infinite moves;
- a written adjudication rule for repeated positions across turns;
- a definition of what counts as a solved result and what auxiliary tables are
  part of the proof.

Exit criteria:

- every terminal and non-terminal case is machine-executable;
- no step of move generation depends on informal judgment.

### Phase 1. Build a Trusted Reference Engine

Goal:
implement a minimal, exact, readable engine before any large-scale search.

Deliverables:

- exact state representation;
- legal move generator;
- move executor with full sow/capture/takasa/infinite handling;
- canonicalization for symmetries;
- deterministic serialization format for states and results.

Validation strategy:

- hand-constructed unit tests from `rules.md`;
- property tests for seed conservation, side ownership, and legal-move
  obligations;
- regression suites for edge cases such as kimbi direction changes and
  takasa-only positions;
- if practical, a second independent implementation for cross-checking.

Exit criteria:

- reference engine passes all rule-based tests;
- random differential testing finds no discrepancies.

### Phase 2. Measure the Game Before Trying to Solve It

Goal:
obtain the first empirical picture of complexity.

Deliverables:

- branching-factor estimates by depth and position class;
- move-length distribution, including takasa relay lengths;
- frequency of forced captures;
- symmetry reduction effectiveness;
- reachable-state sampling statistics;
- catalog of infinite-move candidates and confirmed cycles.

Why this matters:

- it tells us whether a full retrograde attack is realistic;
- it identifies promising decomposition boundaries;
- it prevents committing early to the wrong solver architecture.

### Phase 3. Solve Tractable Subspaces First

Goal:
create exact solved islands that serve as both scientific results and
validation anchors.

Candidate subspaces:

- positions with low total mobility;
- positions with bounded maximum pit occupancy;
- positions after large capture depletion on one side;
- endgames with small numbers of pits containing more than one seed;
- symmetry-reduced classes of positions near terminality.

Deliverables:

- exact tablebases for selected subspaces;
- proofs of subspace completeness;
- value and distance metrics for those subspaces.

Exit criteria:

- tablebases are independently verified and can be queried by the main solver.

### Phase 4. Develop the Main Exact Solver

Goal:
compute the exact value of the initial position.

Expected architecture:

- exact transposition table keyed by canonical state;
- cycle-aware graph search, likely over strongly connected components or an
  equivalent exact framework;
- proof-oriented search from the initial position;
- tablebase probes for solved subspaces;
- distributed execution across GCP CPU machines;
- optional GPU-guided move ordering only if it can be cleanly separated from
  correctness.

Candidate exact methods to evaluate:

- retrograde analysis where the subgraph is finite and well bounded;
- depth-first proof-number search or related proof search;
- alpha-beta style exact search with repetition/cycle treatment only after the
  game graph is formally defined;
- SCC decomposition on the reachable state graph when cycles matter.

Selection criterion:

choose the simplest exact method that matches the observed structure of the
game graph after Phase 2.

### Phase 5. Independent Verification and Reproducibility Package

Goal:
make the result defendable in peer review.

Deliverables:

- independent replay checker for solved lines;
- reproducibility scripts for main experiments;
- exact hardware/runtime logs;
- frozen artifact manifest with hashes;
- written methodology section draft;
- figure/table generation scripts for publication.

Acceptance standard:

- a skeptical reviewer should be able to inspect the rules, rerun the main
  pipelines, and verify the result from stored artifacts.

## GCP Compute Strategy

### CPUs

Primary use:

- exact search;
- transposition tables;
- retrograde passes;
- graph algorithms;
- large-memory state storage;
- verification jobs.

### GPUs

Secondary use:

- heuristic move ordering models;
- state-embedding experiments;
- compression or ranking models for search guidance.

Constraint:

no GPU-produced model may be allowed to alter correctness claims. It may only
change the order in which exact search explores the tree or graph.

## Logging Protocol

Every future work session should append a dated entry containing:

- objective;
- hypothesis or question;
- method;
- files changed;
- commands run;
- hardware used;
- outputs/artifacts generated;
- result;
- interpretation;
- next action.

Negative results must be logged as carefully as positive results.

## Entry 2026-04-04

### Objective

Start the project in a scientifically defensible way by defining the first
research plan and creating a persistent notebook.

### Observations

- Workspace currently contains only `rules.md`.
- The rule specification is unusually strong already and is sufficient to begin
  engineering work.
- The largest immediate scientific gap is the unresolved treatment of repeated
  positions across turns.

### Decisions

- Use this file as the master lab notebook for now.
- Treat solver correctness and solver acceleration as separate concerns.
- Do not claim a strong solution until the ruleset is frozen and executable
  without solver-side conventions that could change outcomes.

### Next Actions

1. Convert `rules.md` into an explicit implementation checklist and identify
   every place where code could go wrong.
2. Design the state representation and move generator interfaces.
3. Implement a trusted reference engine with exhaustive rule tests before any
   large-scale search.
4. Add experiment logging conventions and artifact naming once code exists.

## Entry 2026-04-04 (Reference Engine Scaffold)

### Objective

Translate the formal rules into an implementation checklist and create the
first trusted reference-engine scaffold with rule-focused tests.

### Method

- Chose Python 3.12 as the reference implementation language because it is
  already available locally and supports fast iteration with readable exact
  logic.
- Re-checked a key sowing detail against Donkers' Appendix C before writing
  engine code.
- Implemented a small exact engine first, not an optimized solver.

### Source Verification

Important correction captured before implementation:

- `rules.md` Section 12 pseudocode can be read as if ordinary mtaji sowing
  starts by placing a seed back into the emptied starting pit.
- Donkers Appendix C rule 1.6 states that relay sowing starts at the next pit.
- Donkers Appendix C notation note states that mtaji direction indicates the
  hand movement after picking up stones from the starting pit, which is again
  consistent with next-pit ordinary sowing.
- Capture resowing still starts in the kichwa itself.

Reference used:

- [Donkers thesis PDF](https://project.dke.maastrichtuniversity.nl/games/files/phd/Donkers_thesis.pdf)

### Files Changed

- `implementation_checklist.md`
- `pyproject.toml`
- `bao/__init__.py`
- `bao/reference.py`
- `tests/test_reference.py`

### Commands Run

- `Get-ChildItem -Force`
- `python --version`
- `py -0p`

### Outputs

- implementation checklist translating rules into engine tasks;
- first reference-engine module with:
  state validation,
  move generation,
  exact move execution,
  within-turn infinite-move detection,
  symmetry helpers,
  canonical keys;
- first `unittest` suite for rule edge cases.

### Assumptions

- Current code follows `rules.md` as the project rules baseline, except where
  primary-source verification was needed to disambiguate sowing semantics.
- Infinite-move illegality is enforced exactly at the per-move level by
  repeated pending-sowing states, not by a fixed sow-count threshold.
- Repeated positions across turns remain unresolved at the game-graph level
  and are not yet encoded as a final adjudication rule.

### Next Actions

1. Run the tests and fix any defects in the scaffold.
2. Add more regression cases, especially relay-driven secondary captures.
3. Decide how the engine should classify self-emptying capture attempts, if
   such positions are reachable and outcome-relevant.
4. Add stable state serialization and trace logging for later proof artifacts.

## Entry 2026-04-04 (Source Audit Reset)

### Objective

Reset the rule-freezing process so the project does not rely on `rules.md` as
an assumed authority.

### Reason For Reset

- The existing `rules.md` is useful, but it mixes strong source material with
  solver-side design choices.
- That is risky for a publication-oriented strong solution.
- The right next step is not to trust it harder, but to evidence-grade the
  rules and separate what is primary-source backed from what is not.

### Method

- Re-read the strongest directly accessible primary source, Donkers' Appendix C
  and related Bao discussion.
- Pulled secondary material only for the Bao la Kujifunza variant mapping,
  because the cited 1971 leaflet and full de Voogt thesis were not directly
  available in-session.
- Wrote a new working rules authority that records evidence strength per rule.

### Files Changed

- `formal_rules.md`
- `implementation_checklist.md`

### Key Findings

- Ordinary mtaji sowing should be treated as next-pit sowing, not
  start-pit-inclusive sowing.
- Capture resowing should still begin in the chosen kichwa itself.
- The strongest current working hypothesis for Bao la Kujifunza is still:
  mtaji-stage Bao from a fully populated board, with no takasia and no seeds
  in hand.
- Cross-turn repetition remains unresolved for publication purposes.
- The front-row-empty condition should not be checked at the transient
  pick-up instant when stones are in hand; it should be checked on board
  positions reached during sowing and after captures. Donkers' lone-kichwa
  takasa rule strongly points to this interpretation.

### New Project Rule

- `formal_rules.md` is now the working authority for the engine.
- `rules.md` is background material only.

### Sources Consulted

- Donkers thesis PDF:
  https://project.dke.maastrichtuniversity.nl/games/files/phd/Donkers_thesis.pdf
- Kronenburg article page:
  https://cris.maastrichtuniversity.nl/en/publications/never-ending-moves-in-bao/
- Mancala World Bao la Kujifunza page:
  https://mancala.fandom.com/wiki/Bao_la_Kujifunza
- Wikipedia Bao page:
  https://en.wikipedia.org/wiki/Bao_%28game%29

### Next Actions

1. Re-audit the engine and tests against `formal_rules.md`.
2. Obtain stronger primary evidence for the variant definition if possible.
3. Investigate published treatment of cross-turn repetition before any claim of
   a full strong solution.

## Entry 2026-04-04 (Engine Re-Audit)

### Objective

Check whether the existing reference-engine scaffold still agrees with the new
source-audited rules authority.

### Method

- Ran the local unit-test suite.
- Investigated the resulting failures instead of treating them as ordinary code
  defects.
- Used the failures to refine the operational reading of the front-row-empty
  rule.

### Commands Run

- `python -m unittest discover -s tests -v`

### Result

- Initial test run exposed a contradiction between the engine and Donkers'
  takasa rule for the lone-kichwa case.
- The engine had been checking front-row emptiness too early, at the transient
  moment when stones were lifted into the hand.
- The corrected implementation now checks that loss condition on board
  positions reached during sowing and after captures.
- After the fix, the full current test suite passed.

### Interpretation

This was a useful research result, not just a debugging step. It shows that
even a seemingly simple rule phrase such as "even during a move" needs an
operational interpretation consistent with the rest of the rules.

### Next Actions

1. Add tests for relay-driven secondary captures.
2. Look for stronger primary evidence on the Bao la Kujifunza variant mapping.
3. Start documenting every remaining evidence-`B` or evidence-`C` rule as a
   solver risk item.

## Entry 2026-04-05 (Concrete Move Examples)

### Objective

Turn the reference engine into a tool that can produce concrete, auditable move
examples for regression tests and future publication figures.

### Method

- Extended the reference engine so every executed move records a structured
  sowing trace.
- Added a small example-mining script to search shallow reachable positions.
- Promoted one reachable multi-capture line into the permanent test suite.

### Files Changed

- `bao/reference.py`
- `bao/__init__.py`
- `tests/test_reference.py`
- `tools/find_examples.py`
- `implementation_checklist.md`

### Commands Run

- `python -m unittest discover -s tests -v`
- `python tools\\find_examples.py`
- random-state exploratory search for legal infinite moves over 20,000 sampled
  states and 143,049 pseudo-legal candidate moves

### Results

- The engine now returns per-sowing traces rather than only final boards.
- The initial move `P1i1 clockwise` from the standard start position already
  gives a rich reachable regression case:
  10 sowings, 4 captures, and a stable final board snapshot.
- The current test suite increased to 12 passing tests.
- The shallow example search visited 25 reachable states before finding both:
  a multi-capture example and a takasa example to report.
- The exploratory random-state search did not find an infinite move candidate
  among 20,000 sampled states. This is only a negative scouting result, not a
  claim that such moves are rare in the actual reachable game graph.

### Interpretation

This is a concrete milestone because the rules are no longer only encoded as
 acceptance tests on isolated predicates. We now have a worked move trace from
 the actual initial position that can act as a future regression anchor.

The negative infinite-move search result is also useful: it tells us that
simple random sampling is not a good way to build the infinite-move test set.
We will likely need either literature examples or targeted search heuristics.

### Next Actions

1. Build a targeted search for longer takasa sequences and candidate
   infinite-move structures instead of relying on random sampling.
2. Keep hunting for stronger primary evidence for the Bao la Kujifunza variant
   definition.
3. Start a small measurement script for branching factor and move-length
   statistics on shallow reachable layers.

## Entry 2026-04-05 (Source Hunt and Shallow Profile)

### Objective

Make the project more concrete in two ways:

- determine exactly how strong the current source base really is;
- gather first empirical measurements from the reachable game graph.

### Source-Hunt Outcome

Directly obtained:

- Donkers 2003 thesis PDF, including Appendix C and related Bao discussion.
- Metadata and abstract page for Kronenburg et al. 2006.
- The de Voogt Academia page for *Limits of the Mind*, including its abstract
  and downloadable attachment identifier.

Not directly obtained in-session:

- full text of de Voogt 1995;
- the 1971 National Museum of Tanzania leaflet *How to Play Bao*.

Interpretation:

- mtaji mechanics currently have strong direct support from Donkers;
- the exact mapping from Bao la Kujifunza to mtaji-stage Zanzibar Bao still
  rests on secondary support and cited-but-unretrieved primary material.

### Files Changed

- `tools/profile_shallow.py`

### Commands Run

- `python tools\\profile_shallow.py`

### Shallow Reachability Measurements

Profiled unique states by first discovery from the standard initial position to
depth 4 plies:

- depth 0: 1 state, average branching 16.000, all 16 moves mtaji
- depth 1: 16 states, average branching 6.750, all 108 moves mtaji
- depth 2: 108 states, average branching 4.630, 468 mtaji and 32 takasa moves
- depth 3: 484 states, average branching 3.930, 1,578 mtaji and 324 takasa
  moves

Aggregate over the measured layers:

- 2,486 unique discovered states up to depth 4
- overall average branching 4.148
- overall average sowings per move 5.167
- maximum sowings observed so far: 31
- mtaji average sowings 5.683, maximum 31
- takasa average sowings 2.022, maximum 8

### Interpretation

These first numbers are encouraging because they already show strong structure:

- the opening is capture-dense;
- branching drops quickly over the first few plies;
- takasa appears by depth 2 but is shorter on average than mtaji in the
  measured frontier.

This is not yet enough to choose a final exact-solver architecture, but it is
already enough to justify continuing with measured-state exploration rather
than blind algorithm selection.

### Next Actions

1. Extend the profiler to deeper layers and add canonical-state statistics.
2. Build a targeted search for long takasa chains and infinite-move
   candidates.
3. Keep the variant-definition risk visible until stronger primary evidence is
   found.

## Entry 2026-04-05 (Symmetry-Aware Measurements)

### Objective

Push the empirical work from a first sketch to something more structurally
useful for solver design.

### Files Changed

- `tools/profile_shallow.py`
- `tools/search_extremes.py`
- `implementation_checklist.md`

### Commands Run

- `python -m unittest discover -s tests -v`
- `python tools\\profile_shallow.py --depth 5`
- `python tools\\search_extremes.py --depth 5`

### Verification

- The full current test suite still passes: 12 tests, 0 failures.

### Symmetry-Aware Reachability Profile

Unique states discovered from the initial position by first discovery up to
depth 5 plies:

- depth 0: 1 states, 1 canonical states, average branching 16.000
- depth 1: 16 states, 8 canonical states, average branching 6.750
- depth 2: 108 states, 54 canonical states, average branching 4.630
- depth 3: 484 states, 242 canonical states, average branching 3.930
- depth 4: 1,877 states, 939 canonical states, average branching 3.486

Aggregate totals up to depth 5:

- 8,774 unique states
- 4,388 canonical states
- empirical canonical reduction factor: 2.000
- 292 terminal results encountered
- overall average branching: 3.648
- overall average sowings per move: 5.138
- maximum sowings seen so far: 31
- mtaji average sowings: 5.753, maximum 31
- takasa average sowings: 2.213, maximum 16

### Extreme Reachable Examples Up To Depth 5

Search over canonical reachable states up to depth 5 found:

- longest move so far:
  line `P1o1 clockwise -> P2i3 anti_clockwise -> P1i8 anti_clockwise -> P2i1 clockwise`
  with 31 sowings, 124 seeds sown, 5 captures
- longest takasa so far:
  line `P1o1 clockwise -> P2i5 anti_clockwise -> P1o8 anti_clockwise -> P2i3 clockwise -> P1i3 anti_clockwise`
  with 16 sowings and 60 seeds sown
- most captures in one move so far:
  line `P1o1 clockwise -> P2i3 clockwise -> P1o8 anti_clockwise -> P2i1 clockwise`
  with 8 captures in a single mtaji move

### Interpretation

Two points now look concrete enough to influence solver design:

1. The empirical symmetry reduction is already a clean factor of 2.000 through
   the measured frontier, so symmetry-aware storage should be part of the main
   exact-solver design from the start.
2. Takasa moves are clearly present and can already be substantially long by
   depth 5, but mtaji still dominates both frequency and move length in the
   early reachable graph.

The longest-move examples also show that even shallow reachable play produces
very long multi-sowing turns, so solver instrumentation and logging must stay
first-class rather than optional.

### Next Actions

1. Push the measurements one layer deeper if runtime remains reasonable.
2. Build a targeted search specifically biased toward long takasa and possible
   infinite-move motifs.
3. Start designing the first artifact format for exporting traced example
   lines.

## Entry 2026-04-05 (Depth-6 Reachability)

### Objective

Check whether the depth-5 measurement picture stays stable one ply deeper, or
whether the early conclusions were still too shallow.

### Commands Run

- `python tools\\profile_shallow.py --depth 6`
- `python tools\\search_extremes.py --depth 6`

### Results

Profile through depth 6 plies:

- depth 5 frontier: 6,288 states, 3,144 canonical states
- average branching at depth 5: 3.720
- depth-6 total discovered states: 31,634
- depth-6 total canonical states: 15,818
- empirical canonical reduction factor remains exactly 2.000
- terminal results encountered through the run: 808
- overall average branching through depth 6: 3.700
- overall maximum sowings seen so far: 33
- mtaji maximum sowings increased from 31 to 33
- takasa maximum sowings remained 16

Updated extreme examples through depth 6:

- longest move so far:
  `P1i2 clockwise -> P2i7 anti_clockwise -> P1i4 anti_clockwise -> P2o8 anti_clockwise -> P1i2 clockwise -> P2i6 anti_clockwise`
  with 33 sowings, 139 seeds sown, 5 captures
- longest takasa so far is unchanged from the depth-5 search:
  16 sowings, 60 seeds sown
- most captures in one move is also unchanged:
  8 captures in a single mtaji move

### Interpretation

This deeper run strengthens several earlier impressions:

- symmetry reduction is not just theoretically available; it is empirically
  stable in the measured frontier and should be treated as essential, not
  optional;
- early reachable Bao la Kujifunza remains capture-heavy even as takasa
  becomes common;
- takasa can be long, but the deepest move-length growth in the measured
  frontier is still being driven by mtaji;
- runtime for these measurements is still reasonable enough to continue
  incremental profiling.

### Next Actions

1. Add canonical-state and trace export formats so measured examples can be
   stored as stable artifacts.
2. Build a biased search for long takasa and potential infinite-move motifs.
3. Decide when to switch from generic profiling to the first solver-oriented
   search prototype.

## Entry 2026-04-05 (RuleSpec and Native Scaffold)

### Objective

Start implementing the roadmap as concrete repository structure rather than
leaving it as planning text.

### Method

- Promoted the working rule set into a versioned computational RuleSpec.
- Added a rule-to-test matrix so rule coverage is explicit.
- Added stable canonical state packing and stable trace artifacts on the Python
  side.
- Added a reference corpus builder for future Rust differential testing.
- Scaffolded a native Rust workspace with packed-state and artifact types.

### Files Changed

- `docs/rulespec_v1.md`
- `docs/rule_test_matrix.md`
- `bao/packing.py`
- `bao/artifacts.py`
- `bao/__init__.py`
- `tools/build_corpus.py`
- `Cargo.toml`
- `native/bao_solver_core/Cargo.toml`
- `native/bao_solver_core/src/lib.rs`
- `native/bao_solver_core/src/types.rs`
- `native/bao_solver_core/src/pack.rs`
- `native/bao_solver_core/src/state.rs`
- `native/bao_solver_core/src/artifacts.rs`
- `tests/test_artifacts.py`
- `implementation_checklist.md`

### Results

- RuleSpec now has a version string and explicit `PRIMARY`, `SECONDARY`,
  `CONVENTION`, and `UNRESOLVED` tags.
- The project now has a stable `PackedStateKey` format based on stars-and-bars
  ranking over canonical states.
- The full 32-pit, 64-seed composition fits comfortably inside 16 bytes.
- Trace artifacts now have a deterministic JSON representation suitable for
  later figure generation, appendices, and regression storage.
- A Rust workspace and library scaffold now exist for the native exact core.

### Environment Note

- Rust tooling is not installed in the current environment, so the new native
  crate could not yet be compiled or tested here.

### Verification

- `python -m unittest discover -s tests -v` passed with 18 tests.
- `python tools\\build_corpus.py --depth 2 --output artifacts\\reference_corpus_depth2.jsonl`
  produced the first differential corpus artifact.
- `artifacts\\initial_p1i1_clockwise_trace.json` was emitted successfully as
  the first stable worked trace artifact.

### Next Actions

1. Run and validate the new Python packing and artifact tests.
2. Generate the first differential corpus artifact for the future Rust engine.
3. Install Rust tooling or move onto a machine with Rust available before
   implementing native move generation.

## Entry 2026-04-05 (First Native Differential and Benchmark Loop)

### Objective

Turn the native scaffold into a real cross-language checkpoint and establish
the first repeatable performance baseline for a hot kernel.

### Method

- Compiled the Rust workspace now that `cargo`, `rustc`, and `rustup` are
  available locally.
- Added a corpus-check binary that validates Rust `StateKey` generation
  against the Python-produced reference corpus.
- Added a release-mode benchmark binary and Python wrapper for the packed
  state-key path.

### Files Changed

- `native/bao_solver_core/Cargo.toml`
- `native/bao_solver_core/src/bin/statekey_corpus.rs`
- `native/bao_solver_core/src/bin/bench_statekey.rs`
- `tools/check_native_statekeys.py`
- `tools/run_native_benchmarks.py`
- `implementation_checklist.md`

### Commands Run

- `cargo test`
- `python tools\\check_native_statekeys.py artifacts\\reference_corpus_depth2.jsonl`
- `python -m unittest discover -s tests -v`
- `python tools\\run_native_benchmarks.py --corpus artifacts\\reference_corpus_depth2.jsonl --output artifacts\\benchmarks\\statekey_benchmark_release.json --warmup-iterations 2000 --iterations 200000`

### Results

- Rust unit tests passed.
- The Python-vs-Rust `StateKey` differential check passed on all 9 corpus
  records in `artifacts\\reference_corpus_depth2.jsonl`.
- The full Python test suite still passes with 18 tests.
- The repository now has a repeatable release-mode benchmark harness for the
  `pack_key` and `unpack_key` kernels using the same correctness corpus.
- First release benchmark artifact:
  `artifacts\\benchmarks\\statekey_benchmark_release.json`
  reports:
  `pack_key` = 35.3325726 s over 1,800,000 operations
  (`19,629.207 ns/op`, `50,944.49 ops/s`);
  `unpack_key` = 159.8254704 s over 1,800,000 operations
  (`88,791.928 ns/op`, `11,262.29 ops/s`).

### Interpretation

This is the first true bridge between the reference layer and the native
solver layer. We now have:

- a trusted Python authority,
- a compiling Rust core,
- a corpus-based differential checkpoint between them,
- and a concrete benchmark loop that can be used for autonomous optimization
  sprints.

The first baseline is intentionally modest. It immediately highlights two
important engineering facts:

- packed-state ranking and especially unranking are already expensive enough
  that they deserve dedicated optimization work;
- we should avoid unnecessary unpack operations in the main solver design
  until the representation is faster.

That is still only the state-key slice, not native move generation, but it is
exactly the right thin vertical slice to stabilize before porting more game
logic.

### Next Actions

1. Port canonical legal-move generation into Rust and validate it against
   Python on generated corpora.
2. Expand the differential harness from state-key equivalence to full
   successor-set equivalence.
3. Start an optimization sprint on ranking/unranking and representation
   choices before they become entrenched in graph-building code.

## Entry 2026-04-05 (First Native Move-Generation Port)

### Objective

Move the Rust core beyond packed keys and into actual Bao mechanics, while
keeping the correctness boundary tight enough to differential-check against
the Python reference engine.

### Method

- Ported legal-move generation, winner detection, first-sowing preview, and
  move application into the Rust core.
- Added Rust regression tests mirroring several existing Python reference
  cases.
- Added a corpus-driven native legal-move checker and a Python differential
  script to compare native move sets against the reference engine.

### Files Changed

- `native/bao_solver_core/src/movegen.rs`
- `native/bao_solver_core/src/lib.rs`
- `native/bao_solver_core/src/bin/legal_moves_corpus.rs`
- `tools/check_native_legal_moves.py`
- `implementation_checklist.md`

### Commands Run

- `cargo test`
- `python tools\\check_native_legal_moves.py artifacts\\reference_corpus_depth2.jsonl`
- `python -m unittest discover -s tests -v`

### Results

- The Rust workspace now contains native implementations of:
  legal move generation,
  move-kind classification,
  move application,
  first-sowing preview,
  and winner detection.
- Rust unit tests now include native regressions for:
  initial legal-move shape,
  the standard opening multi-capture line,
  takasa front-row priority,
  lone-kichwa restriction,
  and no-move loss.
- `cargo test` passed with 8 Rust tests.
- The new cross-language legal-move differential check passed on all 9 states
  in `artifacts\\reference_corpus_depth2.jsonl`.
- The Python reference suite still passes with 18 tests.

### Interpretation

This is the first native Bao rules slice with real behavioral parity evidence.
The project has now crossed from “native packing scaffold” to “native game
logic under differential control.”

That matters because future optimization work can now target concrete rule
kernels rather than abstract data structures only. It also means the next
increment should focus on richer successor equivalence, not just move-set
equivalence.

### Next Actions

1. Add successor-result differential checks so Rust and Python agree not only
   on legal moves, but on resulting boards, terminations, and capture counts.
2. Profile the native move-generation path and identify whether ranking,
   canonicalization, or move application is the dominant hot kernel.
3. Decide whether `StateWork` should be reshaped before more solver code is
   built on top of it.

## Entry 2026-04-05 (Successor Differential, Benchmarks, and Native Census)

### Objective

Push the native layer from local move-generation parity into broader evidence:

- full successor-result agreement against Python,
- first release-mode move-path benchmarks,
- and first graph-level reachability measurements from the Rust core.

### Method

- Generated a deeper depth-3 reachable reference corpus.
- Added a native successor exporter and Python differential checker.
- Added a release benchmark for `legal_moves` and `apply_move` over the depth-3
  corpus.
- Added a release-mode native shallow census that mirrors the Python
  reachability profiler.

### Files Changed

- `native/bao_solver_core/src/bin/successor_corpus.rs`
- `tools/check_native_successors.py`
- `native/bao_solver_core/src/bin/bench_movegen.rs`
- `tools/run_native_movegen_benchmarks.py`
- `native/bao_solver_core/src/bin/shallow_census.rs`
- `tools/run_native_shallow_census.py`
- `implementation_checklist.md`

### Commands Run

- `python tools\\build_corpus.py --depth 3 --output artifacts\\reference_corpus_depth3.jsonl`
- `python tools\\check_native_statekeys.py artifacts\\reference_corpus_depth3.jsonl`
- `python tools\\check_native_legal_moves.py artifacts\\reference_corpus_depth3.jsonl`
- `python tools\\check_native_successors.py artifacts\\reference_corpus_depth3.jsonl`
- `python tools\\run_native_movegen_benchmarks.py --corpus artifacts\\reference_corpus_depth3.jsonl --output artifacts\\benchmarks\\movegen_benchmark_release.json --warmup-iterations 500 --iterations 20000`
- `python tools\\run_native_shallow_census.py --depth 6 --output artifacts\\census\\shallow_depth6_release.json`
- `python tools\\profile_shallow.py --depth 6`
- `cargo test`
- `python -m unittest discover -s tests -v`

### Results

- `artifacts\\reference_corpus_depth3.jsonl` now contains 63 reachable
  canonical states from the initial position.
- State-key differential on the depth-3 corpus passed on all 63 records.
- Legal-move differential on the depth-3 corpus passed on all 63 records.
- Full successor-result differential on the depth-3 corpus passed on all 63
  records.
- `artifacts\\benchmarks\\movegen_benchmark_release.json` reports:
  `legal_moves` = 19.0726573 s over 1,260,000 state evaluations
  (`15,137.03 ns/op`, `66,063.16 ops/s`);
  `apply_move` = 12.0337756 s over 6,400,000 legal-move applications
  (`1,880.28 ns/op`, `531,836.41 ops/s`).
- `artifacts\\census\\shallow_depth6_release.json` matches the Python
  reference profiler at depth 6 on the key graph totals:
  31,634 unique states,
  15,818 canonical states,
  canonical reduction factor approximately 2,
  808 terminal results,
  overall average branching approximately 3.700,
  maximum sowings 33,
  takasa maximum sowings 16.
- The release native depth-6 census completed in about 0.204 s wall-clock.
- Verification remains green:
  `cargo test` passed with 8 Rust tests;
  Python `unittest` passed with 18 tests.

### Interpretation

This is a substantial step forward.

The native core is no longer only “plausibly equivalent” to the Python
reference on isolated kernels. It now agrees with the reference on:

- packed canonical state keys,
- legal-move sets,
- full successor results,
- and shallow graph-level reachable-state totals.

That is the first level of evidence strong enough to justify using Rust for
real solver-oriented experimentation rather than only for future plans.

The benchmark results also sharpen the optimization picture:

- `apply_move` itself is relatively fast;
- `legal_moves` is slower because it layers candidate generation,
  classification, and infinite-move filtering on top of move execution;
- ranking and especially unranking remain much slower than move execution and
  should stay on the optimization shortlist.

### Next Actions

1. Add a corpus-based differential check for native per-move traces or, if
   traces remain Python-only for now, explicitly freeze the native/publication
   division of responsibility.
2. Build the first native frontier enumerator that emits canonical state keys
   and successor counts as shard-like artifacts rather than only census
   summaries.
3. Start representation and kernel optimization experiments on the known hot
   areas: state-key ranking/unranking and high-level legal-move generation.

## Entry 2026-04-05 (First Canonical Frontier Artifact)

### Objective

Turn the native reachability work into a durable artifact with payload and
manifest, rather than leaving it as an in-memory census only.

### Method

- Added a Rust frontier exporter that traverses canonical states from the
  initial position.
- Added a Python wrapper that writes the payload, computes a SHA-256 checksum,
  and emits a JSON manifest.
- Corrected the exporter once to ensure its depth semantics include the full
  discovered frontier layer, matching the census convention.

### Files Changed

- `native/bao_solver_core/src/bin/export_frontier.rs`
- `tools/export_native_frontier.py`
- `implementation_checklist.md`

### Commands Run

- `cargo test`
- `python tools\\export_native_frontier.py --depth 6 --output artifacts\\shards\\frontier_depth6.jsonl --manifest artifacts\\shards\\frontier_depth6.manifest.json`

### Results

- `artifacts\\shards\\frontier_depth6.jsonl` was generated as the first
  canonical shard-style payload.
- `artifacts\\shards\\frontier_depth6.manifest.json` was generated with:
  item_count `15,818`,
  payload_bytes `5,455,943`,
  sha256
  `e655a53bf9c97830d6bced3e7029798fd27fae212928e6839c8af8dc5e6ebca4`.
- The manifest item count now matches the native and Python depth-6 canonical
  reachability total exactly.
- Deeper-layer frontier nodes are present in the payload with `outdegree = 0`
  because they are discovered but not expanded beyond the export depth.

### Interpretation

This is the first artifact in the repository that looks like an actual small
state shard rather than a debug printout. It is still JSONL and still shallow,
but it already exercises the important workflow pieces:

- deterministic canonical keys,
- reusable state payload,
- explicit RuleSpec tagging,
- and manifest-level checksums for auditability.

That is a meaningful bridge toward the eventual `StateShard` / `EdgeShard`
pipeline.

### Next Actions

1. Decide whether the next artifact should be:
   flat binary state shards,
   explicit edge shards,
   or a native trace/export path for publication examples.
2. Add terminal annotations to the frontier payload so the shard format starts
   resembling a true solver input rather than only a reachability dump.
3. Start profiling memory footprint and bytes-per-state on the frontier export
   path before moving to larger depths.

## Entry 2026-04-05 (Canonical Graph Slice Artifacts)

### Objective

Move from a single frontier dump to a more solver-like artifact pair:

- a terminal-annotated canonical state shard,
- and an explicit canonical edge shard.

### Method

- Added a Rust graph-slice exporter that traverses the canonical reachable
  graph from the initial position.
- Emitted deterministic state records and edge records in sorted order.
- Split the combined exporter output into separate JSONL payloads via a Python
  wrapper, then wrote per-payload manifests and a summary file.
- Fixed one deterministic-ordering compile issue and one counting expectation
  mismatch by checking the export against the canonical, not raw, graph.

### Files Changed

- `native/bao_solver_core/src/bin/export_graph_slice.rs`
- `tools/export_native_graph_slice.py`
- `implementation_checklist.md`

### Commands Run

- `cargo test`
- `python tools\\export_native_graph_slice.py --depth 6 --states-output artifacts\\shards\\state_slice_depth6.jsonl --states-manifest artifacts\\shards\\state_slice_depth6.manifest.json --edges-output artifacts\\shards\\edge_slice_depth6.jsonl --edges-manifest artifacts\\shards\\edge_slice_depth6.manifest.json --summary-output artifacts\\shards\\graph_slice_depth6.summary.json`
- `python -m unittest discover -s tests -v`

### Results

- `artifacts\\shards\\state_slice_depth6.jsonl` was generated as a
  terminal-annotated canonical state payload.
- `artifacts\\shards\\edge_slice_depth6.jsonl` was generated as the first
  explicit canonical edge payload.
- `artifacts\\shards\\graph_slice_depth6.summary.json` reports:
  `state_count = 15,818`,
  `expanded_state_count = 4,388`,
  `edge_count = 16,243`,
  `terminal_edge_count = 404`,
  `nonterminal_edge_count = 15,839`.
- `artifacts\\shards\\state_slice_depth6.manifest.json` reports:
  payload_bytes `5,487,190`,
  sha256
  `3ac19edc3873956e2e154cf71f59ea57fd91c541beb71036e5c94947cd7e117c`.
- `artifacts\\shards\\edge_slice_depth6.manifest.json` reports:
  payload_bytes `5,721,192`,
  sha256
  `07aecc1f79641017fddb99510e7d4ed2ef10c61033b7f7762e8a07122cb00052`.
- The Python test suite still passes with 18 tests, and Rust tests still pass
  with 8 tests.

### Interpretation

This is the first artifact pair in the repository that resembles a real
solver-input slice:

- nodes and edges are now separated,
- state records carry terminal annotations,
- edge records carry move metadata, terminations, and successor references,
- and both payloads are individually checksummed.

The key subtlety is that this exporter operates on the **canonical graph**, so
its counts should be compared against canonical layer totals, not raw-state
 totals. That is why the expanded canonical state count is `4,388` rather than
 the raw-state count `8,774`.

### Next Actions

1. Add compact binary state and edge payloads so we can begin measuring
   bytes-per-state and bytes-per-edge without JSON overhead.
2. Add dense local IDs or stable per-shard ordering metadata so the edge shard
   starts looking like a future exact-solver input rather than a lookup dump.
3. Profile memory footprint and serialization throughput on the graph-slice
   path before increasing export depth.

## Entry 2026-04-05 (Binary Graph Slice and Verification)

### Objective

Measure the canonical graph slice without JSON overhead and verify that the
compact binary artifacts match their JSONL source shards exactly.

### Method

- Packed the state shard into fixed-width 32-byte records.
- Packed the edge shard into fixed-width 18-byte records using zero-based
  local state IDs.
- Wrote per-payload manifests and a binary summary file.
- Added a verifier that checks the binary payloads record-by-record against
  the JSONL source shards.

### Files Changed

- `tools/build_binary_graph_slice.py`
- `tools/verify_binary_graph_slice.py`
- `implementation_checklist.md`

### Commands Run

- `python tools\\build_binary_graph_slice.py --states-jsonl artifacts\\shards\\state_slice_depth6.jsonl --edges-jsonl artifacts\\shards\\edge_slice_depth6.jsonl --states-binary artifacts\\shards\\state_slice_depth6.bin --states-manifest artifacts\\shards\\state_slice_depth6.bin.manifest.json --edges-binary artifacts\\shards\\edge_slice_depth6.bin --edges-manifest artifacts\\shards\\edge_slice_depth6.bin.manifest.json --summary-output artifacts\\shards\\graph_slice_depth6.binary.summary.json`
- `python tools\\verify_binary_graph_slice.py --state-jsonl artifacts\\shards\\state_slice_depth6.jsonl --state-binary artifacts\\shards\\state_slice_depth6.bin --edge-jsonl artifacts\\shards\\edge_slice_depth6.jsonl --edge-binary artifacts\\shards\\edge_slice_depth6.bin`
- `python -m unittest discover -s tests -v`

### Results

- `artifacts\\shards\\state_slice_depth6.bin` was generated at `506,176`
  bytes.
- `artifacts\\shards\\edge_slice_depth6.bin` was generated at `292,374`
  bytes.
- `artifacts\\shards\\graph_slice_depth6.binary.summary.json` reports:
  `32.0` bytes per state record,
  `18.0` bytes per edge record.
- `artifacts\\shards\\state_slice_depth6.bin.manifest.json` reports sha256
  `05815e3fa6baad21ee754327050f4fec1c93366afca963733a6ca5fee42aa811`.
- `artifacts\\shards\\edge_slice_depth6.bin.manifest.json` reports sha256
  `b4b0f20263e722aa87d247aa712bbdd9d97e9b020cb7d5268e7d09cb4df3cecc`.
- The verifier passed on:
  `15,818` binary state records,
  `16,243` binary edge records,
  `4,388` expanded canonical states,
  `404` terminal edges.
- The Python test suite still passes with 18 tests.

### Interpretation

This is the first concrete bytes-per-record measurement for the project’s
emerging solver input pipeline.

On the current depth-6 canonical slice:

- JSONL state payload: about `5.49 MB`
- binary state payload: about `0.51 MB`
- JSONL edge payload: about `5.72 MB`
- binary edge payload: about `0.29 MB`

So even this very simple fixed-width binary packing gives a large reduction in
artifact size and moves the project much closer to the kind of storage model
needed for large exact search.

### Next Actions

1. Add throughput measurements for JSONL-to-binary conversion and native
   binary export so storage planning is based on both bytes and serialization
   cost.
2. Consider moving the binary shard writer into Rust so the exact-core layer
   owns the full state/edge artifact pipeline end to end.
3. Design the next artifact step around dense successor references and shard
   headers suitable for larger distributed graph construction.

## Entry 2026-04-05 (Native Binary Shard Writer and Throughput Baseline)

### Objective

Move binary shard writing into the Rust exact-core layer and measure the first
end-to-end export throughput for the canonical depth-6 graph slice.

### Method

- Added a native Rust exporter that writes headered binary state and edge
  shards directly.
- Added a Python wrapper that invokes the native exporter, writes manifests,
  and stores the summary artifact.
- Added a verifier that checks the native binary shards record-by-record
  against the JSONL graph-slice source.
- Added a timing harness for the native binary export path.

### Files Changed

- `native/bao_solver_core/src/bin/export_binary_graph_slice.rs`
- `tools/export_native_binary_graph_slice.py`
- `tools/verify_native_binary_graph_slice.py`
- `tools/benchmark_native_binary_export.py`
- `implementation_checklist.md`

### Commands Run

- `cargo test`
- `python tools\\export_native_binary_graph_slice.py --depth 6 --states-output artifacts\\shards\\native_state_slice_depth6.bin --states-manifest artifacts\\shards\\native_state_slice_depth6.manifest.json --edges-output artifacts\\shards\\native_edge_slice_depth6.bin --edges-manifest artifacts\\shards\\native_edge_slice_depth6.manifest.json --summary-output artifacts\\shards\\native_graph_slice_depth6.summary.json`
- `python tools\\verify_native_binary_graph_slice.py --state-jsonl artifacts\\shards\\state_slice_depth6.jsonl --state-binary artifacts\\shards\\native_state_slice_depth6.bin --edge-jsonl artifacts\\shards\\edge_slice_depth6.jsonl --edge-binary artifacts\\shards\\native_edge_slice_depth6.bin`
- `python tools\\benchmark_native_binary_export.py --depth 6 --output artifacts\\benchmarks\\native_binary_export_depth6.json`

### Results

- Native binary state shard:
  `artifacts\\shards\\native_state_slice_depth6.bin`
  with 64-byte header, 32-byte records, 15,818 records, payload size
  `506,240` bytes including header, sha256
  `7bcdbfe1260d5f982b23e8dc7a32e035a99e1484d402906a165c2f9a3ae1dc3f`.
- Native binary edge shard:
  `artifacts\\shards\\native_edge_slice_depth6.bin`
  with 64-byte header, 18-byte records, 16,243 records, payload size
  `292,438` bytes including header, sha256
  `0e45b8f7573554b302b0b4f64d0244b7a7a566a5e8e7e284126a5b8ec289eba6`.
- Native summary artifact:
  `artifacts\\shards\\native_graph_slice_depth6.summary.json`
  confirms:
  state_count `15,818`,
  expanded_state_count `4,388`,
  edge_count `16,243`,
  terminal_edge_count `404`,
  header_bytes `64`.
- The native binary verifier passed on all:
  `15,818` state records,
  `16,243` edge records.
- Export throughput benchmark:
  `artifacts\\benchmarks\\native_binary_export_depth6.json`
  reports approximately:
  `5.311 s` wall-clock,
  `2,978` states/s,
  `3,058` edges/s,
  `150,375` bytes/s.

### Interpretation

This is the first end-to-end shard pipeline owned by the native exact core.

That matters for two reasons:

- the project now has a path from native move generation directly to
  headered binary solver artifacts without passing through JSONL packing;
- storage planning can now use both density and throughput measurements, not
  only fixed record sizes.

The throughput is still modest because the exporter is doing full traversal,
canonicalization, and file writing in one simple path. That is fine at this
stage: the goal was to make the binary pipeline concrete and verifiable before
optimizing it.

### Next Actions

1. Profile the native binary exporter to separate traversal cost from write
   cost and identify the next optimization target.
2. Add shard header readers in Rust or Python utilities so downstream tools can
   consume the native binary format without JSON sidecars.
3. Design local dense successor arrays or grouped adjacency blocks so the edge
   shard format becomes closer to the final exact-solver representation.

## Entry 2026-04-05 (Phase-Timed Native Export and Adjacency Shard)

### Objective

Separate exporter cost into real phases and test a grouped-adjacency edge
layout that removes repeated source IDs from per-edge records.

### Method

- Added per-phase timing to the native binary exporter.
- Extended the native exporter to emit a grouped-adjacency binary shard with
  an offset table and compact adjacency-edge records.
- Added a verifier for the adjacency shard against the canonical JSONL graph
  slice.
- Re-ran the end-to-end native export benchmark with the new summary fields.

### Files Changed

- `native/bao_solver_core/src/bin/export_binary_graph_slice.rs`
- `tools/export_native_binary_graph_slice.py`
- `tools/verify_native_adjacency_graph_slice.py`
- `tools/benchmark_native_binary_export.py`
- `implementation_checklist.md`

### Commands Run

- `cargo test`
- `python tools\\export_native_binary_graph_slice.py --depth 6 --states-output artifacts\\shards\\native_state_slice_depth6.bin --states-manifest artifacts\\shards\\native_state_slice_depth6.manifest.json --edges-output artifacts\\shards\\native_edge_slice_depth6.bin --edges-manifest artifacts\\shards\\native_edge_slice_depth6.manifest.json --adjacency-output artifacts\\shards\\native_adjacency_slice_depth6.bin --adjacency-manifest artifacts\\shards\\native_adjacency_slice_depth6.manifest.json --summary-output artifacts\\shards\\native_graph_slice_depth6.summary.json`
- `python tools\\verify_native_binary_graph_slice.py --state-jsonl artifacts\\shards\\state_slice_depth6.jsonl --state-binary artifacts\\shards\\native_state_slice_depth6.bin --edge-jsonl artifacts\\shards\\edge_slice_depth6.jsonl --edge-binary artifacts\\shards\\native_edge_slice_depth6.bin`
- `python tools\\verify_native_adjacency_graph_slice.py --state-jsonl artifacts\\shards\\state_slice_depth6.jsonl --edge-jsonl artifacts\\shards\\edge_slice_depth6.jsonl --adjacency-binary artifacts\\shards\\native_adjacency_slice_depth6.bin`
- `python tools\\benchmark_native_binary_export.py --depth 6 --output artifacts\\benchmarks\\native_binary_export_depth6.json`
- `python -m unittest discover -s tests -v`

### Results

- Native adjacency shard:
  `artifacts\\shards\\native_adjacency_slice_depth6.bin`
  with sha256
  `f96f25f7e527a9641f6ca007d2585f7247a5e1672539097f1ddd72d81661cce2`.
- Adjacency shard size: `258,256` bytes.
- Flat native edge shard size remains: `292,438` bytes.
- The adjacency verifier passed on:
  `15,818` states,
  `16,243` edges,
  `15,819` offset entries.
- Updated native export phase timings from
  `artifacts\\shards\\native_graph_slice_depth6.summary.json`:
  traversal `449,451,200 ns`,
  sort `2,994,100 ns`,
  local-ID map `1,600,800 ns`,
  state annotation `205,848,000 ns`,
  state write `11,521,100 ns`,
  flat edge write `6,647,400 ns`,
  adjacency write `5,387,900 ns`,
  total `686,669,000 ns`.
- Updated export benchmark from
  `artifacts\\benchmarks\\native_binary_export_depth6.json`:
  elapsed wall-clock about `5.742 s`,
  total written bytes `1,056,934`,
  throughput about `184,080 bytes/s`.

### Interpretation

Two results are now concrete:

1. The grouped-adjacency layout is already better than the flat edge shard for
   this slice.
   It reduces the edge artifact from `292,438` bytes to `258,256` bytes while
   preserving exact verifiability and giving a more solver-friendly access
   pattern.
2. The exporter timing breakdown shows the current bottlenecks clearly.
   Traversal is still the largest phase, but state-level terminal annotation is
   the second-largest cost by a large margin.
   The actual binary writing phases are comparatively small.

This means future optimization effort should focus first on:

- move-generation / traversal cost,
- and the current terminal-annotation strategy,

not on raw file I/O.

### Next Actions

1. Redesign state terminal annotation so the exporter does not spend a large
   fraction of its time recomputing `winner()` over the slice.
2. Decide whether the adjacency shard should replace the flat edge shard as the
   default solver-input edge format.
3. Add small header readers / inspectors for the native binary formats so
   downstream tools can consume them without bespoke parsing code each time.

## Entry 2026-04-05 (Shard Inspection Tooling)

### Objective

Add a lightweight shared reader path for the native shard headers so future
tools do not need to re-derive the binary metadata layout from writer code.

### Method

- Added a Python header inspector for native state, edge, and adjacency
  shards.
- Added a short format note documenting the current header and record layouts.
- Ran the inspector against all three current native shard types.

### Files Changed

- `tools/inspect_native_shard.py`
- `docs/native_shard_formats.md`
- `implementation_checklist.md`

### Commands Run

- `python tools\\inspect_native_shard.py artifacts\\shards\\native_state_slice_depth6.bin artifacts\\shards\\native_edge_slice_depth6.bin artifacts\\shards\\native_adjacency_slice_depth6.bin`
- `python -m unittest discover -s tests -v`

### Results

- The inspector parsed all three shard types successfully.
- Header sanity checks passed for:
  `artifacts\\shards\\native_state_slice_depth6.bin`,
  `artifacts\\shards\\native_edge_slice_depth6.bin`,
  `artifacts\\shards\\native_adjacency_slice_depth6.bin`.
- For every shard, the payload byte count declared in the header matches the
  actual payload length on disk exactly.
- The format note now records:
  common 64-byte header layout,
  current state record layout,
  flat edge record layout,
  adjacency record layout,
  and the inspection command for quick future use.

### Interpretation

This is a small but useful reproducibility step. The project now has:

- native writers,
- native and Python verifiers,
- and a simple shared inspection path for binary artifact metadata.

That reduces the chance of later tool drift around shard headers and record
sizes.

### Next Actions

1. Redesign state terminal annotation to reduce the currently high annotation
   phase cost.
2. Decide whether adjacency should become the default edge artifact for
   solver-facing work.
3. Start planning dense successor blocks or per-state adjacency sections on top
   of the inspected header conventions.

## Entry 2026-04-05 (Terminal Annotation Optimization)

### Objective

Reduce the native exporter's state-annotation cost without weakening
correctness.

### Method

- Added an early-exit `has_legal_move` path in the Rust move generator.
- Changed `winner()` to use that early-exit path rather than materializing the
  full legal-move set when only existence matters.
- Updated the native binary exporter to reuse already-known `outdegree` values
  for expanded states instead of recomputing full winner logic for those
  states.
- Refreshed the native export benchmark so it reports both wall-clock time and
  the exporter’s internal timing.

### Files Changed

- `native/bao_solver_core/src/movegen.rs`
- `native/bao_solver_core/src/lib.rs`
- `native/bao_solver_core/src/bin/export_binary_graph_slice.rs`
- `tools/benchmark_native_binary_export.py`
- `implementation_checklist.md`

### Commands Run

- `cargo test`
- `python tools\\export_native_binary_graph_slice.py --depth 6 --states-output artifacts\\shards\\native_state_slice_depth6.bin --states-manifest artifacts\\shards\\native_state_slice_depth6.manifest.json --edges-output artifacts\\shards\\native_edge_slice_depth6.bin --edges-manifest artifacts\\shards\\native_edge_slice_depth6.manifest.json --adjacency-output artifacts\\shards\\native_adjacency_slice_depth6.bin --adjacency-manifest artifacts\\shards\\native_adjacency_slice_depth6.manifest.json --summary-output artifacts\\shards\\native_graph_slice_depth6.summary.json`
- `python tools\\verify_native_binary_graph_slice.py --state-jsonl artifacts\\shards\\state_slice_depth6.jsonl --state-binary artifacts\\shards\\native_state_slice_depth6.bin --edge-jsonl artifacts\\shards\\edge_slice_depth6.jsonl --edge-binary artifacts\\shards\\native_edge_slice_depth6.bin`
- `python tools\\verify_native_adjacency_graph_slice.py --state-jsonl artifacts\\shards\\state_slice_depth6.jsonl --edge-jsonl artifacts\\shards\\edge_slice_depth6.jsonl --adjacency-binary artifacts\\shards\\native_adjacency_slice_depth6.bin`
- `python tools\\benchmark_native_binary_export.py --depth 6 --output artifacts\\benchmarks\\native_binary_export_depth6.json`
- `python -m unittest discover -s tests -v`

### Results

- Export correctness is unchanged:
  all native shard verifiers still pass.
- The native export summary now reports:
  traversal `314,966,400 ns`,
  state annotation `51,210,600 ns`,
  state write `4,347,800 ns`,
  flat edge write `5,856,800 ns`,
  adjacency write `5,522,100 ns`,
  total `386,752,400 ns`.
- Compared with the earlier phase-timed run:
  state annotation dropped from `205,848,000 ns` to `51,210,600 ns`.
- The refreshed benchmark now distinguishes wrapper overhead from exporter
  work:
  wall-clock elapsed about `0.893 s`,
  internal exporter elapsed about `0.387 s`,
  process overhead about `0.506 s`.
- Internal throughput now reports approximately:
  `40,900` states/s,
  `41,998` edges/s,
  `2.73 MB/s`.

### Interpretation

This optimization is a clear win.

The state-annotation phase fell by roughly `75%`, and the new timing breakdown
 makes the actual cost structure much clearer:

- traversal remains the dominant phase,
- annotation is now much smaller,
- write phases are minor by comparison,
- and process-launch overhead is visible separately from exporter work.

That is exactly the kind of optimization loop we want for the larger-scale
solver pipeline: measure, simplify the hot path, verify, and re-measure.

### Next Actions

1. Decide whether the grouped-adjacency shard should replace the flat edge
   shard as the default solver-facing edge format.
2. Focus the next optimization pass on traversal rather than annotation or
   write phases.
3. Add a reader for adjacency payloads that can iterate successors by local
   state ID without JSONL fallbacks.

## Entry 2026-04-05 (Adjacency Query Path)

### Objective

Add a practical read path for the grouped-adjacency shard so downstream tools
can inspect successors directly by local state ID.

### Method

- Added a Python adjacency query tool that reads the native state shard and
  adjacency shard together.
- Queried both empty-frontier IDs and one expanded state ID to confirm the
  decoded successor ranges look sane in practice.
- Added the query command to the native shard format note.

### Files Changed

- `tools/query_native_adjacency.py`
- `docs/native_shard_formats.md`
- `implementation_checklist.md`

### Commands Run

- `python tools\\query_native_adjacency.py --state-binary artifacts\\shards\\native_state_slice_depth6.bin --adjacency-binary artifacts\\shards\\native_adjacency_slice_depth6.bin --local-id 0`
- `python tools\\query_native_adjacency.py --state-binary artifacts\\shards\\native_state_slice_depth6.bin --adjacency-binary artifacts\\shards\\native_adjacency_slice_depth6.bin --local-id 24`

### Results

- Local ID `0` decodes as an unexpanded depth-6 frontier state with zero
  successors, and the offset table returns an empty range as expected.
- Local ID `24` decodes as an expanded depth-5 state with outdegree `2`, and
  the adjacency reader returns two decoded successor records with:
  move codes `18` and `27`,
  both mtaji,
  both landed-in-empty terminations,
  and the expected result local IDs and canonical keys.

### Interpretation

The grouped-adjacency shard is now not only smaller and verified, but also
practically queryable. That is an important step toward replacing the flat edge
shard in solver-facing workflows.

### Next Actions

1. Decide whether adjacency should become the default edge representation for
   future graph-construction work.
2. Focus optimization effort on traversal, which remains the dominant export
   cost.
3. Consider adding batch adjacency iterators or a small Python/Rust API layer
   instead of only one-shot CLI readers.

## Entry 2026-04-05 (Canonical-Key Slice Query Path)

### Objective

Make the native slice artifacts queryable by canonical state key, not only by
local state ID, so the shard set starts behaving like an oracle boundary.

### Method

- Added a reusable Python shard reader module for native state and adjacency
  shards.
- Implemented binary-search lookup over the sorted native state shard by
  canonical `StateKey`.
- Extended the adjacency query tool to accept either `--local-id` or
  `--state-key-hex`.
- Added summary metadata recording the shard sort order plus the initial
  position's canonical key and local ID.
- Added Python tests that round-trip known local IDs through key lookup and
  verify that query-by-key matches query-by-ID.

### Files Changed

- `bao/native_shards.py`
- `bao/__init__.py`
- `tests/test_native_shards.py`
- `tools/query_native_adjacency.py`
- `native/bao_solver_core/src/bin/export_binary_graph_slice.rs`
- `tools/export_native_binary_graph_slice.py`
- `docs/native_shard_formats.md`
- `implementation_checklist.md`

### Commands Run

- `cargo test`
- `python -m unittest discover -s tests -v`
- `python tools\\export_native_binary_graph_slice.py --depth 6 --states-output artifacts\\shards\\native_state_slice_depth6.bin --states-manifest artifacts\\shards\\native_state_slice_depth6.manifest.json --edges-output artifacts\\shards\\native_edge_slice_depth6.bin --edges-manifest artifacts\\shards\\native_edge_slice_depth6.manifest.json --adjacency-output artifacts\\shards\\native_adjacency_slice_depth6.bin --adjacency-manifest artifacts\\shards\\native_adjacency_slice_depth6.manifest.json --summary-output artifacts\\shards\\native_graph_slice_depth6.summary.json`
- `python tools\\benchmark_native_binary_export.py --depth 6 --output artifacts\\benchmarks\\native_binary_export_depth6.json`
- `python tools\\verify_native_binary_graph_slice.py`
- `python tools\\verify_native_adjacency_graph_slice.py`
- `python tools\\query_native_adjacency.py --local-id 5237`
- `python tools\\query_native_adjacency.py --state-key-hex 000000000002e6f569b0a676d3d209e4`

### Results

- Rust tests still pass: `8` passing.
- Python tests now pass: `20` passing.
- Both native shard verifiers still pass on the regenerated depth-6 slice:
  `15,818` state records and `16,243` edge records validated.
- The depth-6 export summary now includes:
  `sorted_by="canonical_state_key"`,
  `root_state_key_hex="000000000002e6f569b0a676d3d209e4"`,
  `root_local_id=5237`.
- The key-based query path resolves the initial position correctly and returns:
  depth `0`,
  outdegree `16`,
  `8` distinct nonterminal successor states,
  and the full decoded successor list from the adjacency shard.
- The refreshed timed export run reports:
  traversal `163,658,400 ns`,
  state annotation `37,199,300 ns`,
  state write `2,499,300 ns`,
  flat edge write `1,743,100 ns`,
  adjacency write `15,656,200 ns`,
  total `225,198,000 ns`.

### Interpretation

This is a meaningful step toward an oracle and reproducibility layer.

We now have:

- a reusable native shard reader,
- deterministic lookup by canonical state key,
- summary metadata tying the initial position to a stable local ID,
- and tests that exercise the new lookup path directly.

The timing data should be interpreted cautiously. Traversal improved slightly
relative to the prior optimized run, but the total time moved around because
the write and annotation phases showed some run-to-run variance. The main win
here is interface maturity, not a decisive new speedup claim.

### Next Actions

1. Promote the adjacency shard plus key lookup into a small solver-facing API
   instead of only CLI tooling.
2. Add tablebase-friendly terminal annotations so solved-state lookups can be
   answered without extra inference.
3. Start a first slice-local solving scaffold over the adjacency representation
   to exercise policy/value record formats before full graph construction.

## Entry 2026-04-05 (Slice-Local Partial Solver Scaffold)

### Objective

Exercise solver semantics on the native adjacency representation before full
graph construction by building a partial solve over the depth-6 slice.

### Method

- Added a Python partial-solver tool that reads the native state and adjacency
  shards and performs a monotone `win/loss/unknown` fixpoint.
- Treated unexpanded frontier states as `unknown` rather than forcing a false
  loss or win.
- Used terminal edge winners as immediate solved outcomes.
- Added bulk shard decoders after the first correctness-first implementation
  proved much too slow.
- Added regression tests covering the new bulk decoders against the existing
  single-record query path.

### Files Changed

- `tools/solve_slice_partial.py`
- `bao/native_shards.py`
- `bao/__init__.py`
- `tests/test_native_shards.py`
- `implementation_checklist.md`

### Commands Run

- `python tools\\solve_slice_partial.py --output artifacts\\solve\\slice_partial_depth6.json`
- `python -m unittest discover -s tests -v`
- `Measure-Command { python tools\\solve_slice_partial.py --output artifacts\\solve\\slice_partial_depth6.json } | Select-Object TotalSeconds`

### Results

- The initial correctness-first partial solver completed successfully but took
  about `39.8 s` on the depth-6 slice.
- After switching to bulk state and adjacency decoders, the same partial solve
  now completes in about `0.552 s`.
- The solved summary in
  [slice_partial_depth6.json](C:/Users/Chris/Desktop/solve_bao_v2/artifacts/solve/slice_partial_depth6.json)
  is:
  `375` resolved states total,
  `361` partial wins,
  `14` partial losses,
  `15,443` unknown states,
  `4,013` expanded-but-still-unknown states,
  root status `unknown`.
- Python tests now pass with `21` tests green.

### Interpretation

This is an important structural milestone.

We now have a first genuine solver scaffold over the native adjacency format,
and it already demonstrates two useful things:

- the root remains unresolved at depth `6`, which is expected and confirms the
  frontier handling is not spuriously collapsing unknown states into solved
  ones;
- representation quality matters enormously even at small scale, since the
  same logical computation fell from about `40 s` to about `0.55 s` once we
  stopped repeatedly decoding shard structure.

That second point is directly relevant to the eventual distributed exact
solver. Any hot-path Python tooling must use bulk decoding or vectorized
parsers, and the native solver must avoid per-record overhead just as
aggressively.

### Next Actions

1. Add tablebase-friendly terminal annotations to the native state shard so
   slice solving and future solution shards can consume terminal outcomes
   directly.
2. Move from partial slice solving toward an explicit `SolveRecord` artifact
   layout, even if initially only for partial or closed subgraphs.
3. Begin planning the first SCC-aware prototype over a small closed subgraph or
   synthetic graph so the final solving architecture is exercised before
   billion-state scale.

## Entry 2026-04-05 (Terminal-Annotated State Shards And First SolveRecord Artifact)

### Objective

Turn the native slice pipeline into a more solver-ready artifact stack by:

- encoding terminal seeds directly in the state shard,
- emitting a first fixed-width `SolveRecord`-style partial solution shard,
- and exposing direct queries over that solution shard by canonical state key.

### Method

- Reused the two previously reserved bytes in the native state record to store:
  terminal outcome code and terminal remoteness.
- Extended the JSONL graph-slice exporter so state JSON now carries
  `state_terminal_outcome` and `state_terminal_distance` alongside
  `state_terminal_winner`.
- Updated the Python native shard reader and binary verifier to decode and
  validate the new state-record fields.
- Added a dedicated solution-shard module with a fixed-width `8`-byte record
  format aligned to state local IDs.
- Extended the slice-local partial solver so it now writes:
  summary JSON,
  binary solution shard,
  and manifest.
- Added a dedicated verifier for the partial solution shard and a direct query
  tool that resolves records by local ID or canonical state key.

### Files Changed

- `native/bao_solver_core/src/bin/export_binary_graph_slice.rs`
- `native/bao_solver_core/src/bin/export_graph_slice.rs`
- `bao/native_shards.py`
- `bao/solution_shards.py`
- `bao/__init__.py`
- `tools/verify_native_binary_graph_slice.py`
- `tools/solve_slice_partial.py`
- `tools/verify_partial_solution_shard.py`
- `tools/query_partial_solution.py`
- `tools/inspect_native_shard.py`
- `tests/test_solution_shards.py`
- `docs/native_shard_formats.md`
- `implementation_checklist.md`

### Commands Run

- `cargo test`
- `python -m unittest discover -s tests -v`
- `python tools\\export_native_graph_slice.py --depth 6 --states-output artifacts\\shards\\state_slice_depth6.jsonl --states-manifest artifacts\\shards\\state_slice_depth6.manifest.json --edges-output artifacts\\shards\\edge_slice_depth6.jsonl --edges-manifest artifacts\\shards\\edge_slice_depth6.manifest.json --summary-output artifacts\\shards\\graph_slice_depth6.summary.json`
- `python tools\\export_native_binary_graph_slice.py --depth 6 --states-output artifacts\\shards\\native_state_slice_depth6.bin --states-manifest artifacts\\shards\\native_state_slice_depth6.manifest.json --edges-output artifacts\\shards\\native_edge_slice_depth6.bin --edges-manifest artifacts\\shards\\native_edge_slice_depth6.manifest.json --adjacency-output artifacts\\shards\\native_adjacency_slice_depth6.bin --adjacency-manifest artifacts\\shards\\native_adjacency_slice_depth6.manifest.json --summary-output artifacts\\shards\\native_graph_slice_depth6.summary.json`
- `python tools\\benchmark_native_binary_export.py --depth 6 --output artifacts\\benchmarks\\native_binary_export_depth6.json`
- `python tools\\verify_native_binary_graph_slice.py`
- `python tools\\verify_native_adjacency_graph_slice.py`
- `python tools\\solve_slice_partial.py --output artifacts\\solve\\slice_partial_depth6.json --solution-output artifacts\\solve\\slice_partial_depth6.bin --solution-manifest artifacts\\solve\\slice_partial_depth6.manifest.json`
- `python tools\\verify_partial_solution_shard.py`
- `python tools\\query_partial_solution.py --state-key-hex 000000000002e6f569b0a676d3d209e4`

### Results

- Rust tests remain green: `8` passing.
- Python tests now pass: `22` passing.
- Native binary graph-slice verification still passes:
  `15,818` state records,
  `16,243` edge records,
  `4,388` expanded states,
  `404` terminal edges.
- The refreshed native export timing summary is now:
  traversal `152,322,500 ns`,
  state annotation `22,175,900 ns`,
  state write `2,498,300 ns`,
  flat edge write `2,269,400 ns`,
  adjacency write `2,333,300 ns`,
  total `183,872,300 ns`.
- The depth-6 partial solution shard at
  [slice_partial_depth6.bin](C:/Users/Chris/Desktop/solve_bao_v2/artifacts/solve/slice_partial_depth6.bin)
  has:
  `15,818` records,
  `375` resolved records,
  `8` bytes/record,
  payload `126,608` bytes including the fixed header,
  manifest SHA-256
  `c077e5605b38a609ea08ed2915b8be55a669c3b78bf7c0c1f10c93daf8c196f4`.
- The partial summary at
  [slice_partial_depth6.json](C:/Users/Chris/Desktop/solve_bao_v2/artifacts/solve/slice_partial_depth6.json)
  now records:
  `361` partial wins,
  `14` partial losses,
  root still `unknown`,
  root distance `null`,
  and solution record size `8`.
- The new solution query tool resolves the initial state by canonical key and
  reports an unknown partial record with:
  no best move,
  no distance,
  `partial=true`,
  `frontier_dependent=true`.

### Interpretation

This is the first point where we have a genuine three-layer artifact chain:

1. state shard,
2. adjacency shard,
3. solution shard.

That matters because the final strong-solve pipeline will depend on exactly
that separation of concerns. We now have:

- explicit terminal seeds in the state layer,
- successor structure in the edge layer,
- and value/policy records in the solution layer.

The partial solution shard is not the final solver output, but it is already a
useful contract artifact. It can be verified independently, queried by state
key, and swapped out later for exact solved records without changing the basic
consumer shape.

### Next Actions

1. Add a small solver-facing API that combines state, adjacency, and solution
   lookups into one oracle-style interface.
2. Extend the partial solution artifact to store richer provenance flags once
   SCC-aware solving begins.
3. Start a small SCC/fixpoint prototype over a closed subgraph or synthetic
   graph so the exact solving architecture is exercised before we scale out.

## Entry 2026-04-05 (SCC Slice Solver And Depth-9 Expansion)

### Objective

Push beyond the depth-6 partial slice and start exercising an exact
SCC-oriented solving architecture on larger native slices.

### Method

- Added a reusable SCC/fixpoint solver module with Tarjan decomposition over
  abstract move graphs.
- Added synthetic unit tests covering:
  SCC grouping,
  acyclic win/loss propagation,
  pure unresolved cycles,
  and unknown-frontier handling.
- Built a depth-slice SCC solver that:
  reads the native state and adjacency shards,
  constructs the expanded-state move graph,
  treats unexpanded frontier targets as external unknowns,
  solves the expanded graph by SCC order,
  writes a local-ID-aligned solution shard,
  and emits SCC statistics.
- Ran deeper shallow census passes to depth `8` and `9`.
- Attempted depth `10` census locally; it did not finish within a `20` minute
  timeout window.
- Added a resumable pipeline runner that bundles census, export, verification,
  SCC solve, and manifest writing for longer local or GCP jobs.

### Files Changed

- `bao/scc_solver.py`
- `bao/__init__.py`
- `tests/test_scc_solver.py`
- `tools/solve_slice_scc.py`
- `tools/run_depth_pipeline.py`
- `docs/depth_pipeline.md`
- `implementation_checklist.md`

### Commands Run

- `python -m unittest discover -s tests -v`
- `python tools\\run_native_shallow_census.py --depth 8 --output artifacts\\census\\shallow_depth8_release.json`
- `python tools\\run_native_shallow_census.py --depth 9 --output artifacts\\census\\shallow_depth9_release.json`
- `python tools\\run_native_shallow_census.py --depth 10 --output artifacts\\census\\shallow_depth10_release.json`
  with a `20` minute timeout, which expired
- `python tools\\export_native_binary_graph_slice.py --depth 9 --states-output artifacts\\shards\\native_state_slice_depth9.bin --states-manifest artifacts\\shards\\native_state_slice_depth9.manifest.json --edges-output artifacts\\shards\\native_edge_slice_depth9.bin --edges-manifest artifacts\\shards\\native_edge_slice_depth9.manifest.json --adjacency-output artifacts\\shards\\native_adjacency_slice_depth9.bin --adjacency-manifest artifacts\\shards\\native_adjacency_slice_depth9.manifest.json --summary-output artifacts\\shards\\native_graph_slice_depth9.summary.json`
- `python tools\\export_native_graph_slice.py --depth 9 --states-output artifacts\\shards\\state_slice_depth9.jsonl --states-manifest artifacts\\shards\\state_slice_depth9.manifest.json --edges-output artifacts\\shards\\edge_slice_depth9.jsonl --edges-manifest artifacts\\shards\\edge_slice_depth9.manifest.json --summary-output artifacts\\shards\\graph_slice_depth9.summary.json`
- `python tools\\verify_native_binary_graph_slice.py --state-jsonl artifacts\\shards\\state_slice_depth9.jsonl --state-binary artifacts\\shards\\native_state_slice_depth9.bin --edge-jsonl artifacts\\shards\\edge_slice_depth9.jsonl --edge-binary artifacts\\shards\\native_edge_slice_depth9.bin`
- `python tools\\verify_native_adjacency_graph_slice.py --state-jsonl artifacts\\shards\\state_slice_depth9.jsonl --edge-jsonl artifacts\\shards\\edge_slice_depth9.jsonl --adjacency-binary artifacts\\shards\\native_adjacency_slice_depth9.bin`
- `python tools\\solve_slice_scc.py --state-binary artifacts\\shards\\native_state_slice_depth9.bin --adjacency-binary artifacts\\shards\\native_adjacency_slice_depth9.bin --graph-summary artifacts\\shards\\native_graph_slice_depth9.summary.json --output artifacts\\solve\\slice_scc_depth9.json --solution-output artifacts\\solve\\slice_scc_depth9.bin --solution-manifest artifacts\\solve\\slice_scc_depth9.manifest.json --scc-summary-output artifacts\\analysis\\scc_depth9.json`
- `python tools\\verify_partial_solution_shard.py --state-binary artifacts\\shards\\native_state_slice_depth9.bin --solution-binary artifacts\\solve\\slice_scc_depth9.bin --summary-json artifacts\\solve\\slice_scc_depth9.json`
- `python tools\\run_depth_pipeline.py --depth 6 --output-dir artifacts\\pipeline\\depth6_smoke --skip-jsonl --skip-census`

### Results

- Python tests now pass with `26` tests green.
- Depth `8` shallow census:
  `420,050` unique states,
  `210,026` canonical states,
  max sowings `44`.
- Depth `9` shallow census:
  `1,556,036` unique states,
  `778,019` canonical states,
  terminal results encountered `63,652`,
  max sowings `53`.
- Depth `9` binary graph slice verifies successfully against JSONL:
  `778,019` state records,
  `814,499` edge records,
  `210,026` expanded canonical states,
  `31,826` terminal edges.
- Depth `9` SCC slice solve artifact:
  [slice_scc_depth9.bin](C:/Users/Chris/Desktop/solve_bao_v2/artifacts/solve/slice_scc_depth9.bin)
  with `778,019` records and `25,860` resolved states.
- Depth `9` root result remains `unknown`.
- SCC structure at depth `9` is still trivial in a very important sense:
  `210,026` components for `210,026` expanded states,
  largest component size `1`,
  nontrivial SCC count `0`.
- The depth-9 solver summary reports:
  `24,964` wins,
  `896` losses,
  `752,159` unknowns,
  `134,408` frontier-dependent unresolved components,
  `49,758` closed unresolved components.

### Interpretation

This is a strong and useful result even though it is not yet the full strong
solution.

Up through depth `9`, the expanded slice still behaves as a DAG. That means:

- the root remains unsolved because the slice frontier is too shallow,
  not because we have already run into local repetition cycles near the root;
- the exact-solver infrastructure can continue to exploit DAG-style propagation
  for these early layers;
- and the real cyclic regime is deeper than the currently exported slices.

The depth-10 timeout is also operationally important. Local one-shot census is
already becoming inconvenient there, which strengthens the case for checkpointed
pipeline runs on GCP VMs.

### Next Actions

1. Use the new depth pipeline on a remote machine to push beyond depth `9`
   without interactive babysitting.
2. Add a combined oracle API that can answer state, edge, and solution queries
   from one entry point over arbitrary slice depths.
3. Begin redesigning slice expansion around checkpoints/frontiers so depth `10+`
   does not require full restart from the initial position on every run.

## 2026-04-05 - Live Pipeline Progress for GCP Runs

### Goal

Make the long-running depth pipeline visibly interactive on remote machines so
we can tell whether a run is expanding, exporting, solving, or hung without
needing side-channel process inspection.

### Files Changed

- `tools/run_depth_pipeline.py`
- `tools/export_native_binary_graph_slice.py`
- `tools/export_native_graph_slice.py`
- `tools/run_native_shallow_census.py`
- `tools/solve_slice_scc.py`
- `bao/scc_solver.py`
- `native/bao_solver_core/src/bin/export_binary_graph_slice.rs`
- `docs/depth_pipeline.md`

### Changes

- Changed the top-level depth pipeline to stream merged child output live
  instead of capturing it silently until step completion.
- Added explicit stage start, skip, completion, and failure lines in the
  pipeline driver.
- Enabled unbuffered Python child execution from the pipeline so progress lines
  appear promptly.
- Added live progress lines to the native binary-export wrapper and the SCC
  slice solver.
- Added Rust-side exporter progress on stderr for each depth layer and each
  major write phase.
- Added SCC solver progress hooks so large SCC passes report phase changes and
  component-solve progress.

### Expected Effect

- Remote `tmux` sessions should now show:
  step entry,
  Rust export depth-layer growth,
  SCC graph-build progress,
  SCC phase changes,
  and final pipeline completion.

### Validation Plan

1. Run the Python test suite locally.
2. Run the Rust test suite locally.
3. Rerun the remote depth-10 pipeline and confirm live output appears inside
   `tmux` within the first few seconds.

## 2026-04-05 - Parallel Native Export for Depth Runs

### Goal

Fix the major GCP runtime mistake in the binary slice exporter: frontier
expansion was single-threaded, so a `96`-vCPU VM was effectively being used as a
single-core machine during the hottest phase of depth-10 export.

### Files Changed

- `native/bao_solver_core/Cargo.toml`
- `native/bao_solver_core/src/bin/export_binary_graph_slice.rs`

### Changes

- Added `rayon` to the native crate.
- Parallelized per-state frontier expansion inside each exported depth layer.
- Parallelized edge sorting and canonical state-key sorting.
- Parallelized terminal-state annotation over the sorted state set.
- Added intra-layer progress logging so large frontiers now report
  `processed/total` while the exporter is still inside the same layer.
- Preserved artifact semantics:
  terminal states are still emitted as successor states when the native move
  result carries a board,
  and final shard ordering is still normalized by canonical-key and explicit
  sorting.

### Validation

- `cargo test` passed with `8` Rust tests green after introducing `rayon`.
- `python tools\run_depth_pipeline.py --depth 6 --output-dir artifacts\pipeline\parallel_export_smoke --skip-jsonl --skip-census`
  completed successfully.
- The smoke run produced the expected verified depth-6 totals:
  `15,818` states,
  `4,388` expanded states,
  `16,243` edges,
  `375` resolved states.

### Interpretation

- The main depth-export bottleneck is now using native data parallelism instead
  of one core.
- The previous remote depth-10 run should be considered obsolete from an
  efficiency standpoint and can be restarted after pulling the new code.
- SCC solving is still Python-side and remains a later parallelization target,
  but the binary exporter was the right first fix because it was the stage that
  visibly pinned one core on the GCP VM.

### Next Actions

1. Push the parallel-export patch to GitHub.
2. Abort the old single-threaded depth-10 VM run.
3. Pull the new commit on GCP and rerun depth 10.
4. Measure actual depth-10 wall time and CPU utilization under the parallel
   exporter before deciding whether the SCC stage also needs native
   parallelization immediately.

## 2026-04-05 - Native DAG Solve Fast Path

### Goal

Remove the next depth-pipeline bottleneck after export parallelization. Once the
binary exporter became fast, the Python SCC/slice solver dominated depth-10
runtime even though the expanded root-region graph was still acyclic.

### Files Changed

- `native/bao_solver_core/src/bin/solve_slice_dag.rs`
- `tools/solve_slice_scc_native.py`
- `tools/run_depth_pipeline.py`

### Changes

- Added a native Rust solver fast path for DAG slices.
- The native solver:
  parses the native state and adjacency shards,
  checks whether the expanded slice is a DAG using topological sort,
  solves it exactly by reverse topological propagation,
  writes the normal solution shard and solve summary,
  and emits a compact DAG-analysis summary.
- Added a Python wrapper that prefers the native DAG solver and falls back to
  the existing Python SCC solver only if a cycle is detected.
- Switched the depth pipeline to call the new wrapper instead of the pure-Python
  SCC entrypoint directly.

### Validation

- `cargo test` passed after adding the new binary.
- `python -m unittest discover -s tests -v` still passed with `26` tests green.
- `python tools\run_depth_pipeline.py --depth 6 --output-dir artifacts\pipeline\native_solve_smoke --skip-jsonl --skip-census`
  passed end-to-end.
- Native depth-9 DAG solve matched the previous verified Python depth-9 slice
  exactly on:
  `state_count`,
  `expanded_state_count`,
  `resolved_state_count`,
  `resolved_win_count`,
  `resolved_loss_count`,
  `unknown_state_count`,
  `largest_component_size`,
  `closed_unresolved_component_count`,
  `frontier_dependent_component_count`,
  and `root_status`.
- The native depth-9 DAG solve completed in about `0.29s` of solver time for
  `210,026` expanded states, versus the earlier Python SCC solve taking on the
  order of tens of seconds on comparable DAG slices.

### Interpretation

- This is the right speedup for the current root-region regime.
- As long as the expanded slice remains acyclic, we should not be paying Python
  SCC costs.
- The wrapper preserves correctness because genuine cyclic slices still fall
  back to the older SCC implementation.

### Next Actions

1. Push the native DAG fast path to GitHub.
2. Pull it on the GCP VM.
3. Run depth `11` with the updated pipeline.
4. If depth `11` also remains a DAG, keep using the native fast path while
   building the first native true-SCC fallback for the deeper cyclic regime.

## 2026-04-05 - Optimization Harness for Agent Loops

### Goal

Turn the current hot paths into safe optimization targets for iterative agent
loops by providing:

- deterministic correctness gates,
- direct release-binary benchmarking,
- repeated performance trials,
- and memory metrics on Linux.

### Files Changed

- `benchmarks/hot_path_expectations.json`
- `tools/run_optimization_harness.py`
- `docs/optimization_harness.md`
- `README.md`

### Changes

- Added deterministic expectations for the current hot paths:
  `export_binary_graph_slice` and `solve_slice_dag`.
- The expectations pin exact summary subsets and exact SHA-256 hashes at depths
  `6` and `9`.
- Added a new harness driver that:
  builds the release binary outside measured trials,
  runs correctness gates first,
  runs repeated timed trials,
  and captures Linux peak RSS via `/usr/bin/time -v` when available.
- Added a solver benchmark mode that can reuse prebuilt larger benchmark shards
  through explicit state/adjacency/summary paths, which is important for GCP
  depth-`10+` agent loops.

### Validation

- `python -m py_compile tools\run_optimization_harness.py`
- `python tools\run_optimization_harness.py export_binary --benchmark-depth 6 --trials 1 --output artifacts\benchmarks\export_binary_harness_smoke.json`
- `python tools\run_optimization_harness.py solve_slice_dag --benchmark-depth 6 --trials 1 --output artifacts\benchmarks\solve_slice_dag_harness_smoke.json`
- `python -m unittest discover -s tests -v`

All of the above passed.

### Interpretation

- The hot-path benchmarks are now in the right shape for iterative agent loops.
- A loop can mutate the target function, rerun the harness, and reject any
  change that fails the deterministic gates before looking at performance.
- On Linux GCP machines, the same harness will also report peak RSS, so both
  speed and memory can be used in acceptance decisions.

### Next Actions

1. Push the harness to GitHub.
2. Pull it on the GCP VM.
3. Run the harness there on:
   `export_binary` with a deeper benchmark depth,
   and `solve_slice_dag` with the depth-`11` prebuilt shards.
4. Then let the autonomous optimization loop iterate against those reports.
