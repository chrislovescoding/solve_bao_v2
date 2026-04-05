# Bao la Kujifunza Formal Rules (Source-Audited Working Authority)

## Status

This file is now the working authority for engine and solver development.
`rules.md` should be treated as provisional background only.

This is intentionally not presented as a final publication text yet. Instead,
it records what is currently well supported, what is only secondarily
supported, and what remains unresolved.

## Evidence Grades

- `A`: direct primary-source support available and checked
- `B`: secondary-source support only, or primary source cited but not yet
  obtained directly
- `C`: unresolved for publication purposes

## Sources Used

### Primary

- `A1` Jeroen Donkers, *Nosce Hostem: Searching with Opponent Models* (2003),
  Appendix C "Zanzibar Bao Rules for the Computer" and related Bao chapters.
  PDF: https://project.dke.maastrichtuniversity.nl/games/files/phd/Donkers_thesis.pdf
- `A2` T. Kronenburg, H.H.L.M. Donkers, A.J. de Voogt, "Never-Ending Moves in
  Bao", *ICGA Journal* 29(2), 2006. Metadata/abstract page:
  https://cris.maastrichtuniversity.nl/en/publications/never-ending-moves-in-bao/

### Secondary

- `B1` Mancala World, "Bao la Kujifunza":
  https://mancala.fandom.com/wiki/Bao_la_Kujifunza
- `B2` Wikipedia, "Bao (game)":
  https://en.wikipedia.org/wiki/Bao_%28game%29

### Important Missing Primary Source

- `M1` National Museum of Tanzania leaflet, *How to Play Bao* (1971), cited by
  secondary sources as an early description of Bao la Kujifunza. I have not
  yet obtained a copy.
- `M2` A.J. de Voogt, *Limits of the Mind: Towards a Characterisation of Bao
  Mastership* (1995). This is repeatedly cited as the core ethnographic rules
  source, but I have not yet obtained the full text directly in this session.

## Working Definition of the Variant

### 1. What game are we solving?

Working definition:

- Bao la Kujifunza is the mtaji-stage ruleset of Zanzibar Bao, played from a
  fully populated board with no seeds in hand, and without takasia.

Evidence: `B`

Why only `B`:

- `B1` states this explicitly and cites Nino Vessella.
- `B2` independently agrees that Bao la Kujifunza begins directly in mtaji
  because there are no seeds in hand.
- I have not yet obtained `M1`, the 1971 National Museum of Tanzania leaflet,
  or the full de Voogt text to confirm the variant directly from a primary
  description.

Project decision:

- Use this variant definition as the current working hypothesis.
- Do not call the ruleset publication-frozen until `M1` or `M2` is obtained,
  or until we can show this assumption does not affect the claimed result.

### 2. Initial position

- The board has 32 pits, 4 rows by 8 columns.
- Each player owns two adjacent rows.
- Each pit starts with 2 seeds.
- Total seeds: 64.
- South/Player 1 moves first.

Evidence: `B`

Rationale:

- This follows directly from the working variant definition above and is
  corroborated by `B1` and `B2`.

## Rules Adopted with Stronger Support

The following rules are taken from the mtaji-stage rules in `A1` and are
currently the strongest available basis for implementation.

### 3. Board structure and named pits

- Each player has an inner row and an outer row.
- The inner-row end pits are the two kichwa.
- The kimbi are inner-row columns 1, 2, 7, and 8.
- In Bao la Kujifunza, the nyumba should currently be treated as an ordinary
  pit unless later primary evidence for the variant says otherwise.

Evidence:

- board structure, kichwa, kimbi: `A`
- ordinary-house behavior in this variant: `B`

### 4. Ordinary sowing starts from the next pit

- In ordinary mtaji sowing, after picking up the seeds from the chosen pit,
  sowing proceeds into the next pit in the chosen direction.
- The emptied starting pit does not receive the first seed of the ordinary
  sowing.

Evidence: `A`

Reasoning:

- `A1` rule 1.6 says endelea continues by sowing from the next pit.
- `A1` notation note states that mtaji direction indicates the hand movement
  after picking up the stones of a pit.
- Together these support next-pit ordinary sowing.

### 5. Capture resowing starts in the chosen kichwa itself

- When a capture occurs, the captured seeds are resown from a kichwa.
- The chosen kichwa receives the first captured seed.

Evidence: `A`

Reasoning:

- `A1` rule 1.4 says sowing of captured stones must start at one of the
  kichwa.
- `A1` rule 1.4a ties start-kichwa choice directly to resowing direction.

### 6. Direction rules

- On the first sowing of a move, the player chooses clockwise or
  anti-clockwise.
- Direction cannot change within a single sowing.
- During takasa, direction cannot change during the move.
- During mtaji, a kimbi capture forces the corresponding kichwa and can change
  direction.
- A non-kimbi capture sustains the current direction.

Evidence: `A`

### 7. Move classes

- If the first sowing of a move ends in a capturing condition, the move is
  mtaji.
- If the first sowing does not capture, the move is takasa and no later
  capture is allowed during that move.
- If any mtaji move exists, the player must choose a mtaji move.

Evidence: `A`

### 8. Captures can occur after relay sowing in mtaji

- During mtaji, later sowings in the same move can also trigger captures.
- If endelea reaches a capturing condition, the move continues with the
  capture.

Evidence: `A`

### 9. Mtaji-start restriction

- A capture move in mtaji stage must start from a pit containing more than one
  but fewer than 16 stones.
- Therefore a pit with 16 or more stones cannot start a capturing move, even
  if the landing pit would otherwise allow a capture.

Evidence: `A`

### 10. Takasa restrictions

- If no mtaji move exists, the player must takasa.
- If possible, takasa must start from the front row.
- If the only filled front-row pit is a kichwa, takasa cannot start in the
  direction that immediately enters the back row.

Evidence: `A`

### 11. End of the game

- A player loses if their inner row becomes empty, even during a move.
- A player also loses if they have no legal move.

Evidence: `A`

Operational interpretation for the engine:

- Do not treat the transient act of lifting stones into the hand as an
  immediate front-row-loss event by itself.
- Instead, check the front-row-loss condition on board positions reached during
  sowing and after captures.
- This reading fits Donkers' mtaji takasa rule 3.5b, which specifically bans
  the lone-kichwa direction that would leave the front row empty once sowing
  goes into the back row; the other direction therefore remains playable.

## Infinite-Move Policy

### 12. Never-ending moves inside a turn

- Donkers explicitly adds a computer-play rule under which infinite moves are
  illegal.
- Kronenburg et al. discuss never-ending moves and their rule implications.

Evidence: `A`

Project decision:

- For the engine, detect within-turn infinite moves exactly by repeated
  pending-sowing states rather than by a crude sow-count threshold.
- This is a stricter implementation of Donkers' computer-play intent and is
  preferable for solver work.

### 13. Cross-turn repetitions

Current status:

- I do not yet have a primary or otherwise authoritative adjudication rule for
  repeated whole-board positions across turns.

Evidence: `C`

Project decision:

- Do not hard-code a publication-level rule for cross-turn repetitions yet.
- We can continue building the reference engine and move generator, but a
  journal-grade strong solution must not depend on an unexamined repetition
  convention.

## Current Working Ruleset for Code

Until better evidence appears, the project should implement:

1. the mtaji-stage rules from `A1`;
2. no takasia;
3. no seeds in hand;
4. initial position with 2 seeds in every pit;
5. ordinary sowing from the next pit;
6. capture resowing from the chosen kichwa itself;
7. exact within-turn infinite-move detection;
8. no final solver claim about cross-turn repetitions yet.

## Next Research Actions

1. Obtain the 1971 National Museum of Tanzania leaflet, if possible.
2. Obtain the full de Voogt 1995 thesis text, if possible.
3. Search specifically for any published computational adjudication of
   cross-turn repetition in Bao.
4. Re-audit the move generator against this file and downgrade or revise any
   code path that currently relies on only secondary evidence.
