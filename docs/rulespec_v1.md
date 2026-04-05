# Bao la Kujifunza RuleSpec v1.0.0-draft

## Status

This is the versioned computational ruleset for solver artifacts, benchmarks,
and future paper claims.

- Claim target: full strong solution of Bao la Kujifunza under RuleSpec
  v1.0.0-draft
- Source baseline: [formal_rules.md](C:\Users\Chris\Desktop\solve_bao_v2\formal_rules.md)
- Artifact tag: `rulespec-v1.0.0-draft`

This document is the working computational authority. It is allowed to contain
explicit computational conventions where the historical-source record is not
yet complete, but every such convention must be called out.

## Status Tags

- `PRIMARY`: directly supported by checked primary sources
- `SECONDARY`: supported by secondary sources or cited-but-not-retrieved
  primary sources
- `CONVENTION`: explicit computational convention adopted for solver work
- `UNRESOLVED`: publication gate; final paper claim cannot ignore this item

## Paper Claim

The current target paper claim is:

"Bao la Kujifunza is strongly solved under RuleSpec v1.0.0-draft."

This claim is publishable only if every `UNRESOLVED` item below is closed by:

1. direct source adjudication,
2. explicit computational convention disclosed in the paper title and methods,
   or
3. proof that the issue is unreachable or value-irrelevant in the solved game
   graph.

## Rule Set

### RS-001 Variant Identity

Status: `SECONDARY`

Bao la Kujifunza is treated as the mtaji-stage rules of Zanzibar Bao played
from a fully populated board, with no seeds in hand and without takasia.

### RS-002 Initial Position

Status: `SECONDARY`

- 32 pits arranged as 4 rows of 8
- 2 seeds in every pit
- 64 total seeds
- South moves first

### RS-003 Player Board Topology

Status: `PRIMARY`

Each player owns 16 pits arranged as a closed sowing loop consisting of an
inner row and an outer row.

### RS-004 Named Inner-Row Pits

Status: `PRIMARY`

- kichwa: inner-row columns 1 and 8
- kimbi: inner-row columns 1, 2, 7, and 8

### RS-005 Ordinary Sowing Start

Status: `PRIMARY`

Ordinary sowing starts from the next pit after the picked-up pit in the chosen
direction.

### RS-006 Capture Resowing Start

Status: `PRIMARY`

Capture resowing starts in the chosen kichwa itself, and that kichwa receives
the first captured seed.

### RS-007 Initial Direction Choice

Status: `PRIMARY`

On the first sowing of a move, the player may choose clockwise or
anti-clockwise, subject to move legality constraints.

### RS-008 Fixed Direction Within Sowing

Status: `PRIMARY`

Direction cannot change within a single sowing.

### RS-009 Mtaji Classification

Status: `PRIMARY`

A move is mtaji if and only if its first sowing ends in a capturing
condition.

### RS-010 Takasa Classification

Status: `PRIMARY`

If a move does not start with a capture, no capture is allowed later in that
move.

### RS-011 Mandatory Capture

Status: `PRIMARY`

If any legal mtaji move exists, the player must choose a mtaji move.

### RS-012 Capture Timing

Status: `PRIMARY`

During mtaji, captures may occur after relay sowing as well as after the first
sowing.

### RS-013 Mtaji Start Threshold

Status: `PRIMARY`

A starting pit with 16 or more seeds cannot start a capturing move.

### RS-014 Takasa Front-Row Priority

Status: `PRIMARY`

If no mtaji move exists and any front-row pit contains at least 2 seeds,
takasa must start from the front row.

### RS-015 Lone-Kichwa Takasa Restriction

Status: `PRIMARY`

If the only filled front-row pit is a kichwa, takasa may not start in the
direction that immediately enters the back row.

### RS-016 Kimbi Capture Restart

Status: `PRIMARY`

- capture on columns 1 or 2 restarts from the left kichwa clockwise
- capture on columns 7 or 8 restarts from the right kichwa anti-clockwise

### RS-017 Non-Kimbi Capture Restart

Status: `PRIMARY`

Capture on columns 3 through 6 sustains the current direction and therefore
restarts from the corresponding kichwa.

### RS-018 End of Move by Empty Landing

Status: `PRIMARY`

A move ends when the last seed of a sowing lands in a pit that was empty
before that seed was placed.

### RS-019 Front-Row Loss Condition

Status: `PRIMARY`

A player loses if their front row becomes empty during a move or before their
turn.

Operational reading:

- the transient moment of lifting seeds into the hand is not itself treated as
  a board position for adjudication;
- front-row emptiness is checked on board positions reached during sowing and
  after captures.

### RS-020 No-Move Loss Condition

Status: `PRIMARY`

A player loses if they have no legal move on their turn.

### RS-021 Infinite Within-Turn Moves

Status: `PRIMARY`

Never-ending moves inside a turn are illegal.

### RS-022 Infinite-Move Detector

Status: `CONVENTION`

The reference engine treats a move as infinite if a pending-sowing state
repeats exactly during that move.

### RS-023 Cross-Turn Repetition

Status: `UNRESOLVED`

No final adjudication rule is frozen yet for repeated whole-board positions
across turns.

### RS-024 Self-Emptying Front-Row Cases

Status: `UNRESOLVED`

It remains to be shown whether every self-emptying front-row attempt is fully
covered by the current operational reading or whether a special adjudication
case is still needed.

## Required Artifact Semantics

- All stored `StateKey` values represent canonical positions only.
- Canonical positions are normalized to South-to-move perspective.
- All solver artifacts must record the RuleSpec version string.
- Any future change to an `UNRESOLVED` or `CONVENTION` item requires a new
  RuleSpec version.

## Immediate Publication Gates

Before any final strong-solution claim, the project must close:

- `RS-001`
- `RS-002`
- `RS-023`
- `RS-024`

