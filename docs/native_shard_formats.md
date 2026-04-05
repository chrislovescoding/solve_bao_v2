# Native Shard Formats

This document records the current binary shard layouts emitted by the native
Rust tools. It is a working engineering reference, not yet the final paper
specification.

## Common Header

All current native binary shard files begin with a fixed 64-byte header:

- bytes `0..8`: ASCII magic
- bytes `8..10`: format version, little-endian `u16`
- bytes `10..12`: header size in bytes, little-endian `u16`
- bytes `12..14`: primary record size in bytes, little-endian `u16`
- bytes `14..16`: depth limit, little-endian `u16`
- bytes `16..24`: record count, little-endian `u64`
- bytes `24..32`: payload byte count after the header, little-endian `u64`
- bytes `32..40`: auxiliary count, little-endian `u64`
- bytes `40..64`: ASCII RuleSpec version, zero-padded

Current magics:

- `BAOSTATE`: native canonical state shard
- `BAOEDGE!`: native flat edge shard
- `BAOADJ!!`: native adjacency edge shard

## State Shard

Current file:

- [native_state_slice_depth6.bin](C:/Users/Chris/Desktop/solve_bao_v2/artifacts/shards/native_state_slice_depth6.bin)

Primary record size: `32` bytes

State record layout:

- bytes `0..16`: canonical `StateKey`, big-endian 16-byte payload
- byte `16`: depth
- byte `17`: flags
- byte `18`: terminal outcome code
- byte `19`: terminal remoteness
- bytes `20..24`: outdegree, little-endian `u32`
- bytes `24..28`: nonterminal successor count, little-endian `u32`
- bytes `28..32`: terminal move count, little-endian `u32`

State flags:

- bit `0`: expanded
- bits `1..2`: terminal winner code
  - `0`: none
  - `1`: south
  - `2`: north

Terminal outcome code:

- `0`: no terminal annotation
- `1`: win for side to move
- `2`: loss for side to move
- `3`: reserved for draw/other future conventions

Terminal remoteness:

- `0`: terminal now
- `255`: no terminal remoteness annotation

Header `aux_count` currently stores expanded-state count.

State records are currently emitted in ascending canonical `StateKey` order.
That makes the state shard directly binary-searchable by state key without a
separate index file.

## Flat Edge Shard

Current file:

- [native_edge_slice_depth6.bin](C:/Users/Chris/Desktop/solve_bao_v2/artifacts/shards/native_edge_slice_depth6.bin)

Primary record size: `18` bytes

Flat edge record layout:

- bytes `0..4`: source local state ID, little-endian `u32`
- bytes `4..8`: result local state ID, little-endian `u32`
  - terminal sentinel: `4294967295`
- bytes `8..10`: sowings, little-endian `u16`
- bytes `10..12`: seeds sown, little-endian `u16`
- bytes `12..14`: capture count, little-endian `u16`
- byte `14`: move code
- byte `15`: source depth
- byte `16`: flags
- byte `17`: reserved

Edge flags:

- bit `0`: mtaji move
- bit `1`: infinite move
- bits `2..4`: termination code
  - `0`: none
  - `1`: landed in empty
  - `2`: current player front row empty
  - `3`: opponent front row empty
  - `4`: infinite move
- bits `5..6`: terminal winner code
  - `0`: none
  - `1`: south
  - `2`: north

Header `aux_count` currently stores terminal-edge count.

## Adjacency Edge Shard

Current file:

- [native_adjacency_slice_depth6.bin](C:/Users/Chris/Desktop/solve_bao_v2/artifacts/shards/native_adjacency_slice_depth6.bin)

Primary record size: `12` bytes

Header `record_count` stores edge count.
Header `aux_count` stores state count.

Immediately after the 64-byte header, the file stores an offset table of
`state_count + 1` little-endian `u32` values. The offset range for local state
ID `i` is:

- start edge index: `offsets[i]`
- end edge index: `offsets[i + 1]`

Adjacency edge record layout:

- bytes `0..4`: result local state ID, little-endian `u32`
  - terminal sentinel: `4294967295`
- bytes `4..6`: sowings, little-endian `u16`
- bytes `6..8`: seeds sown, little-endian `u16`
- byte `8`: capture count
- byte `9`: move code
- byte `10`: flags
- byte `11`: reserved

Flags use the same encoding as the flat edge shard.

## Inspection Tool

Use:

```powershell
python tools\inspect_native_shard.py `
  artifacts\shards\native_state_slice_depth6.bin `
  artifacts\shards\native_edge_slice_depth6.bin `
  artifacts\shards\native_adjacency_slice_depth6.bin
```

This prints the parsed header fields and basic sanity checks for each shard.

## Adjacency Query Tool

Use:

```powershell
python tools\query_native_adjacency.py `
  --state-binary artifacts\shards\native_state_slice_depth6.bin `
  --adjacency-binary artifacts\shards\native_adjacency_slice_depth6.bin `
  --local-id 24
```

This prints:

- the decoded local state record,
- the adjacency shard header,
- the successor count for the chosen local ID,
- and the decoded adjacency records for that state.

The same tool can also resolve a state by canonical key:

```powershell
python tools\query_native_adjacency.py `
  --state-binary artifacts\shards\native_state_slice_depth6.bin `
  --adjacency-binary artifacts\shards\native_adjacency_slice_depth6.bin `
  --state-key-hex 000000000002e6f569b0a676d3d209e4
```

The current export summary at
[native_graph_slice_depth6.summary.json](C:/Users/Chris/Desktop/solve_bao_v2/artifacts/shards/native_graph_slice_depth6.summary.json)
records both:

- `sorted_by="canonical_state_key"`
- `root_state_key_hex` and `root_local_id` for the initial position

That makes the slice self-describing enough for a first oracle-style query
path.

## Solution Shard

Current file:

- [slice_partial_depth6.bin](C:/Users/Chris/Desktop/solve_bao_v2/artifacts/solve/slice_partial_depth6.bin)

Primary record size: `8` bytes

Header `record_count` stores state count.
Header `aux_count` stores resolved-record count.

Solution records are local-ID aligned with the state shard. Record `i` is the
current solution record for local state ID `i`.

Solution record layout:

- byte `0`: outcome code
- byte `1`: best move code
  - sentinel `255` means no move stored
- bytes `2..6`: distance/remoteness, little-endian `u32`
  - sentinel `4294967295` means no remoteness stored
- byte `6`: flags
- byte `7`: reserved

Outcome code:

- `0`: unknown
- `1`: win
- `2`: loss
- `3`: reserved for draw/other future conventions

Solution flags:

- bit `0`: partial record
- bit `1`: terminal seed
- bit `2`: frontier-dependent or otherwise unresolved in the current partial solve

Current semantics:

- resolved records in the partial solution shard are exact with respect to the
  proved depth-6 slice;
- unknown records remain unsolved in the current partial artifact;
- distances are stored only for resolved records.

## Partial Solution Query Tool

Use:

```powershell
python tools\query_partial_solution.py `
  --state-binary artifacts\shards\native_state_slice_depth6.bin `
  --solution-binary artifacts\solve\slice_partial_depth6.bin `
  --state-key-hex 000000000002e6f569b0a676d3d209e4
```

This prints:

- the decoded state record,
- the solution-shard header,
- and the aligned `SolveRecord`-style partial solution entry for that state.
