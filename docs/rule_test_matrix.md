# Rule-to-Test Matrix

This matrix ties RuleSpec identifiers to executable coverage in the reference
implementation and highlights remaining validation gaps.

| Rule ID | Summary | Current coverage | Status |
|---|---|---|---|
| `RS-001` | Variant identity | `docs/rulespec_v1.md` only | `TODO` |
| `RS-002` | Initial position | `test_initial_state_has_expected_shape` | `DONE` |
| `RS-003` | Player board topology | `test_regular_sowing_starts_at_next_pit`, `test_capture_resowing_includes_the_kichwa` | `DONE` |
| `RS-004` | Named inner-row pits | Covered indirectly by move tests using fixed pit indices | `DONE` |
| `RS-005` | Ordinary sowing start | `test_regular_sowing_starts_at_next_pit`, `test_preview_of_initial_capture_uses_next_pit_semantics` | `DONE` |
| `RS-006` | Capture resowing start | `test_capture_resowing_includes_the_kichwa`, `test_initial_clockwise_move_has_multi_capture_trace` | `DONE` |
| `RS-007` | Initial direction choice | `test_mandatory_capture_blocks_non_capturing_opening` | `DONE` |
| `RS-008` | Fixed direction within sowing | `test_initial_clockwise_move_has_multi_capture_trace` | `DONE` |
| `RS-009` | Mtaji classification | `test_mandatory_capture_blocks_non_capturing_opening`, `test_initial_clockwise_move_has_multi_capture_trace` | `DONE` |
| `RS-010` | Takasa classification | `test_lone_kichwa_front_row_direction_remains_playable`, `test_takasa_uses_front_row_when_possible` | `DONE` |
| `RS-011` | Mandatory capture | `test_mandatory_capture_blocks_non_capturing_opening` | `DONE` |
| `RS-012` | Capture timing during relay | `test_initial_clockwise_move_has_multi_capture_trace` | `DONE` |
| `RS-013` | Mtaji start threshold | `test_greater_than_fifteen_rule_disables_mtaji_start` | `DONE` |
| `RS-014` | Takasa front-row priority | `test_takasa_uses_front_row_when_possible` | `DONE` |
| `RS-015` | Lone-kichwa takasa restriction | `test_lone_kichwa_cannot_takasa_toward_the_back_row` | `DONE` |
| `RS-016` | Kimbi capture restart | `test_initial_clockwise_move_has_multi_capture_trace` | `DONE` |
| `RS-017` | Non-kimbi capture restart | `test_initial_clockwise_move_has_multi_capture_trace` | `DONE` |
| `RS-018` | End of move by empty landing | `test_lone_kichwa_front_row_direction_remains_playable` | `DONE` |
| `RS-019` | Front-row loss condition | `test_lone_kichwa_front_row_direction_remains_playable` | `DONE` |
| `RS-020` | No-move loss condition | `test_winner_reports_no_move_loss` | `DONE` |
| `RS-021` | Infinite within-turn moves illegal | No literature fixture yet | `TODO` |
| `RS-022` | Infinite-move detector convention | No explicit repeating-pending-state fixture yet | `TODO` |
| `RS-023` | Cross-turn repetition | No frozen adjudication | `BLOCKED` |
| `RS-024` | Self-emptying front-row cases | No explicit proof or dedicated fixture | `TODO` |

