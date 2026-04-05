from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from .packing import canonical_state_key_hex
from .reference import GameState, Move, MoveResult, Player, SowingEvent, pit_label

RULESPEC_VERSION = "rulespec-v1.0.0-draft"
RULESPEC_PATH = "docs/rulespec_v1.md"


@dataclass(frozen=True)
class TraceSowingArtifact:
    sequence_index: int
    start: int
    start_label: str
    seeds: int
    direction: str
    placement_mode: str
    path: tuple[int, ...]
    path_labels: tuple[str, ...]
    landing_pit: int
    landing_label: str
    capture_triggered: bool
    captured_pit: int | None
    captured_label: str | None
    captured_count: int
    board_after_sowing: tuple[int, ...]
    board_after_capture: tuple[int, ...] | None


@dataclass(frozen=True)
class TraceArtifact:
    rulespec_version: str
    rulespec_path: str
    source_state: tuple[int, ...]
    source_to_move: str
    source_state_key_hex: str
    move_start: int
    move_start_label: str
    move_direction: str
    move_kind: str
    sowings: int
    seeds_sown: int
    infinite_move: bool
    terminal_winner: str | None
    termination: str | None
    board_snapshot: tuple[int, ...]
    result_state: tuple[int, ...] | None
    result_to_move: str | None
    result_state_key_hex: str | None
    trace: tuple[TraceSowingArtifact, ...]


@dataclass(frozen=True)
class ShardManifest:
    artifact_type: str
    rulespec_version: str
    code_revision: str
    item_count: int
    payload_bytes: int
    sha256: str
    notes: tuple[str, ...] = ()


def _player_name(player: Player | None) -> str | None:
    if player is None:
        return None
    return "south" if player is Player.SOUTH else "north"


def _event_to_artifact(sequence_index: int, event: SowingEvent) -> TraceSowingArtifact:
    return TraceSowingArtifact(
        sequence_index=sequence_index,
        start=event.start,
        start_label=pit_label(event.start),
        seeds=event.seeds,
        direction=event.direction.value,
        placement_mode=event.placement_mode.value,
        path=event.path,
        path_labels=tuple(pit_label(pit) for pit in event.path),
        landing_pit=event.landing_pit,
        landing_label=pit_label(event.landing_pit),
        capture_triggered=event.capture_triggered,
        captured_pit=event.captured_pit,
        captured_label=pit_label(event.captured_pit) if event.captured_pit is not None else None,
        captured_count=event.captured_count,
        board_after_sowing=event.board_after_sowing,
        board_after_capture=event.board_after_capture,
    )


def trace_artifact_from_result(source_state: GameState, move: Move, result: MoveResult) -> TraceArtifact:
    return TraceArtifact(
        rulespec_version=RULESPEC_VERSION,
        rulespec_path=RULESPEC_PATH,
        source_state=source_state.pits,
        source_to_move=_player_name(source_state.to_move) or "south",
        source_state_key_hex=canonical_state_key_hex(source_state),
        move_start=move.start,
        move_start_label=pit_label(move.start),
        move_direction=move.direction.value,
        move_kind=result.move_kind.value,
        sowings=result.sowings,
        seeds_sown=result.seeds_sown,
        infinite_move=result.infinite_move,
        terminal_winner=_player_name(result.terminal_winner),
        termination=result.termination.value if result.termination is not None else None,
        board_snapshot=result.board_snapshot,
        result_state=result.state.pits if result.state is not None else None,
        result_to_move=_player_name(result.state.to_move) if result.state is not None else None,
        result_state_key_hex=canonical_state_key_hex(result.state) if result.state is not None else None,
        trace=tuple(_event_to_artifact(index, event) for index, event in enumerate(result.trace, start=1)),
    )


def _trace_sowing_to_dict(event: TraceSowingArtifact) -> dict[str, object]:
    return {
        "sequence_index": event.sequence_index,
        "start": event.start,
        "start_label": event.start_label,
        "seeds": event.seeds,
        "direction": event.direction,
        "placement_mode": event.placement_mode,
        "path": list(event.path),
        "path_labels": list(event.path_labels),
        "landing_pit": event.landing_pit,
        "landing_label": event.landing_label,
        "capture_triggered": event.capture_triggered,
        "captured_pit": event.captured_pit,
        "captured_label": event.captured_label,
        "captured_count": event.captured_count,
        "board_after_sowing": list(event.board_after_sowing),
        "board_after_capture": list(event.board_after_capture) if event.board_after_capture is not None else None,
    }


def trace_artifact_to_dict(artifact: TraceArtifact) -> dict[str, object]:
    return {
        "rulespec_version": artifact.rulespec_version,
        "rulespec_path": artifact.rulespec_path,
        "source_state": list(artifact.source_state),
        "source_to_move": artifact.source_to_move,
        "source_state_key_hex": artifact.source_state_key_hex,
        "move_start": artifact.move_start,
        "move_start_label": artifact.move_start_label,
        "move_direction": artifact.move_direction,
        "move_kind": artifact.move_kind,
        "sowings": artifact.sowings,
        "seeds_sown": artifact.seeds_sown,
        "infinite_move": artifact.infinite_move,
        "terminal_winner": artifact.terminal_winner,
        "termination": artifact.termination,
        "board_snapshot": list(artifact.board_snapshot),
        "result_state": list(artifact.result_state) if artifact.result_state is not None else None,
        "result_to_move": artifact.result_to_move,
        "result_state_key_hex": artifact.result_state_key_hex,
        "trace": [_trace_sowing_to_dict(event) for event in artifact.trace],
    }


def trace_artifact_to_json(artifact: TraceArtifact) -> str:
    return json.dumps(trace_artifact_to_dict(artifact), sort_keys=True, separators=(",", ":"))


def write_trace_artifact(path: str | Path, artifact: TraceArtifact) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(trace_artifact_to_json(artifact) + "\n", encoding="ascii")
    return destination

