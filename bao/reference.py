from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum


class Player(IntEnum):
    SOUTH = 0
    NORTH = 1

    @property
    def opponent(self) -> "Player":
        return Player.NORTH if self is Player.SOUTH else Player.SOUTH


class Direction(Enum):
    CLOCKWISE = "clockwise"
    ANTICLOCKWISE = "anti_clockwise"


class MoveKind(Enum):
    MTAJI = "mtaji"
    TAKASA = "takasa"


class MoveTermination(Enum):
    LANDED_IN_EMPTY = "landed_in_empty"
    CURRENT_PLAYER_FRONT_ROW_EMPTY = "current_player_front_row_empty"
    OPPONENT_FRONT_ROW_EMPTY = "opponent_front_row_empty"
    INFINITE_MOVE = "infinite_move"


class PlacementMode(Enum):
    START_PIT = "start_pit"
    NEXT_PIT = "next_pit"


@dataclass(frozen=True)
class Move:
    start: int
    direction: Direction


@dataclass(frozen=True)
class GameState:
    pits: tuple[int, ...]
    to_move: Player

    def __post_init__(self) -> None:
        pits = tuple(int(value) for value in self.pits)
        object.__setattr__(self, "pits", pits)
        if len(pits) != 32:
            raise ValueError("A Bao state must contain exactly 32 pits.")
        if any(value < 0 for value in pits):
            raise ValueError("Pit counts must be non-negative.")
        if sum(pits) != 64:
            raise ValueError("Bao la Kujifunza states must contain exactly 64 seeds.")


@dataclass(frozen=True)
class FirstSowingPreview:
    landing_pit: int
    board_after_sowing: tuple[int, ...]
    capture_possible: bool


@dataclass(frozen=True)
class MoveResult:
    state: GameState | None
    move_kind: MoveKind
    sowings: int
    seeds_sown: int
    board_snapshot: tuple[int, ...]
    trace: tuple["SowingEvent", ...] = ()
    infinite_move: bool = False
    terminal_winner: Player | None = None
    termination: MoveTermination | None = None


@dataclass(frozen=True)
class PendingSowing:
    board: tuple[int, ...]
    start: int
    seeds: int
    direction: Direction
    placement_mode: PlacementMode


@dataclass(frozen=True)
class SowingEvent:
    start: int
    seeds: int
    direction: Direction
    placement_mode: PlacementMode
    path: tuple[int, ...]
    landing_pit: int
    board_after_sowing: tuple[int, ...]
    capture_triggered: bool
    captured_pit: int | None = None
    captured_count: int = 0
    board_after_capture: tuple[int, ...] | None = None


ROW_INNER = "inner"
ROW_OUTER = "outer"

SOUTH_INNER = tuple(range(0, 8))
SOUTH_OUTER = tuple(range(8, 16))
NORTH_INNER = tuple(range(16, 24))
NORTH_OUTER = tuple(range(24, 32))

PLAYER_ROWS = {
    Player.SOUTH: {ROW_INNER: SOUTH_INNER, ROW_OUTER: SOUTH_OUTER},
    Player.NORTH: {ROW_INNER: NORTH_INNER, ROW_OUTER: NORTH_OUTER},
}

PLAYER_LOOPS = {
    Player.SOUTH: {
        Direction.CLOCKWISE: (0, 1, 2, 3, 4, 5, 6, 7, 15, 14, 13, 12, 11, 10, 9, 8),
        Direction.ANTICLOCKWISE: (0, 8, 9, 10, 11, 12, 13, 14, 15, 7, 6, 5, 4, 3, 2, 1),
    },
    Player.NORTH: {
        Direction.CLOCKWISE: (16, 17, 18, 19, 20, 21, 22, 23, 31, 30, 29, 28, 27, 26, 25, 24),
        Direction.ANTICLOCKWISE: (16, 24, 25, 26, 27, 28, 29, 30, 31, 23, 22, 21, 20, 19, 18, 17),
    },
}

NEXT_PIT: dict[tuple[Player, Direction, int], int] = {}
for player, direction_map in PLAYER_LOOPS.items():
    for direction, loop in direction_map.items():
        for index, pit in enumerate(loop):
            NEXT_PIT[(player, direction, pit)] = loop[(index + 1) % len(loop)]


def initial_state() -> GameState:
    return GameState((2,) * 32, Player.SOUTH)


def pit_index(player: Player, row: str, column: int) -> int:
    if row not in (ROW_INNER, ROW_OUTER):
        raise ValueError(f"Unknown row: {row}")
    if column < 1 or column > 8:
        raise ValueError(f"Column must be between 1 and 8, got {column}.")
    base = 0 if player is Player.SOUTH else 16
    if row == ROW_OUTER:
        base += 8
    return base + (column - 1)


def pit_label(index: int) -> str:
    player = player_of_pit(index)
    row = "i" if is_inner_pit(index) else "o"
    return f"P{1 if player is Player.SOUTH else 2}{row}{column_of(index)}"


def player_of_pit(index: int) -> Player:
    if 0 <= index < 16:
        return Player.SOUTH
    if 16 <= index < 32:
        return Player.NORTH
    raise ValueError(f"Invalid pit index: {index}")


def column_of(index: int) -> int:
    return (index % 8) + 1


def is_inner_pit(index: int) -> bool:
    return index in SOUTH_INNER or index in NORTH_INNER


def belongs_to_player(index: int, player: Player) -> bool:
    return player_of_pit(index) is player


def is_kichwa(index: int) -> bool:
    return is_inner_pit(index) and column_of(index) in (1, 8)


def is_left_kichwa(index: int) -> bool:
    return is_inner_pit(index) and column_of(index) == 1


def is_right_kichwa(index: int) -> bool:
    return is_inner_pit(index) and column_of(index) == 8


def is_kimbi(index: int) -> bool:
    return is_inner_pit(index) and column_of(index) in (1, 2, 7, 8)


def pit_sequence(
    player: Player,
    start: int,
    direction: Direction,
    count: int,
    *,
    include_start: bool,
) -> tuple[int, ...]:
    if count < 0:
        raise ValueError("Sowing count must be non-negative.")
    if not belongs_to_player(start, player):
        raise ValueError("The starting pit must belong to the sowing player.")

    current = start if include_start else NEXT_PIT[(player, direction, start)]
    sequence: list[int] = []
    for _ in range(count):
        sequence.append(current)
        current = NEXT_PIT[(player, direction, current)]
    return tuple(sequence)


def preview_first_sowing(state: GameState, move: Move) -> FirstSowingPreview:
    _validate_move_shape(state, move)
    seeds = state.pits[move.start]
    if seeds < 2:
        raise ValueError("The starting pit must contain at least 2 stones.")

    board = list(state.pits)
    board[move.start] = 0
    _, landing_pit, _, _ = _sow(
        board,
        state.to_move,
        move.start,
        seeds,
        move.direction,
        PlacementMode.NEXT_PIT,
    )
    capture_possible = (
        seeds < 16
        and is_inner_pit(landing_pit)
        and belongs_to_player(landing_pit, state.to_move)
        and board[landing_pit] > 1
        and board[_opposite_inner_pit(landing_pit)] > 0
    )
    return FirstSowingPreview(landing_pit, tuple(board), capture_possible)


def legal_moves(state: GameState) -> list[Move]:
    if _winner_if_front_row_empty(state.pits) is not None:
        return []

    candidates = _capture_start_moves(state)
    if not candidates:
        candidates = _takasa_candidates(state)

    finite_moves: list[Move] = []
    for move in candidates:
        result = apply_move(state, move, validate=False)
        if not result.infinite_move:
            finite_moves.append(move)
    return finite_moves


def apply_move(state: GameState, move: Move, *, validate: bool = True) -> MoveResult:
    move_kind = _classify_move_kind(state, move)
    if validate and move not in legal_moves(state):
        raise ValueError(f"Illegal move: {pit_label(move.start)} {move.direction.value}")

    board = list(state.pits)
    seeds = board[move.start]
    board[move.start] = 0

    pending = PendingSowing(
        board=tuple(board),
        start=move.start,
        seeds=seeds,
        direction=move.direction,
        placement_mode=PlacementMode.NEXT_PIT,
    )
    visited: set[PendingSowing] = set()
    sowings = 0
    seeds_sown = 0
    trace: list[SowingEvent] = []

    while True:
        if pending in visited:
            return MoveResult(
                state=GameState(pending.board, state.to_move.opponent),
                move_kind=move_kind,
                sowings=sowings,
                seeds_sown=seeds_sown,
                board_snapshot=pending.board,
                trace=tuple(trace),
                infinite_move=True,
                termination=MoveTermination.INFINITE_MOVE,
            )
        visited.add(pending)

        board = list(pending.board)
        path, landing_pit, placed_count, front_row_winner = _sow(
            board,
            state.to_move,
            pending.start,
            pending.seeds,
            pending.direction,
            pending.placement_mode,
        )
        sowings += 1
        seeds_sown += placed_count

        if front_row_winner is not None:
            return _terminal_result(
                board,
                state.to_move,
                move_kind,
                sowings=sowings,
                seeds_sown=seeds_sown,
                winner=front_row_winner,
                trace=tuple(
                    trace
                    + [
                        SowingEvent(
                            start=pending.start,
                            seeds=pending.seeds,
                            direction=pending.direction,
                            placement_mode=pending.placement_mode,
                            path=path,
                            landing_pit=landing_pit,
                            board_after_sowing=tuple(board),
                            capture_triggered=False,
                        )
                    ]
                ),
            )

        if board[landing_pit] == 1:
            return MoveResult(
                state=GameState(tuple(board), state.to_move.opponent),
                move_kind=move_kind,
                sowings=sowings,
                seeds_sown=seeds_sown,
                board_snapshot=tuple(board),
                trace=tuple(
                    trace
                    + [
                        SowingEvent(
                            start=pending.start,
                            seeds=pending.seeds,
                            direction=pending.direction,
                            placement_mode=pending.placement_mode,
                            path=path,
                            landing_pit=landing_pit,
                            board_after_sowing=tuple(board),
                            capture_triggered=False,
                        )
                    ]
                ),
                termination=MoveTermination.LANDED_IN_EMPTY,
            )

        if (
            move_kind is MoveKind.MTAJI
            and belongs_to_player(landing_pit, state.to_move)
            and is_inner_pit(landing_pit)
            and board[_opposite_inner_pit(landing_pit)] > 0
        ):
            captured = board[_opposite_inner_pit(landing_pit)]
            board_after_sowing = tuple(board)
            board[_opposite_inner_pit(landing_pit)] = 0
            trace.append(
                SowingEvent(
                    start=pending.start,
                    seeds=pending.seeds,
                    direction=pending.direction,
                    placement_mode=pending.placement_mode,
                    path=path,
                    landing_pit=landing_pit,
                    board_after_sowing=board_after_sowing,
                    capture_triggered=True,
                    captured_pit=_opposite_inner_pit(landing_pit),
                    captured_count=captured,
                    board_after_capture=tuple(board),
                )
            )
            front_row_winner = _winner_if_front_row_empty(tuple(board))
            if front_row_winner is not None:
                return _terminal_result(
                    board,
                    state.to_move,
                    move_kind,
                    sowings=sowings,
                    seeds_sown=seeds_sown,
                    winner=front_row_winner,
                    trace=tuple(trace),
                )

            capture_start, capture_direction = _capture_restart(state.to_move, landing_pit, pending.direction)
            pending = PendingSowing(
                board=tuple(board),
                start=capture_start,
                seeds=captured,
                direction=capture_direction,
                placement_mode=PlacementMode.START_PIT,
            )
            continue

        trace.append(
            SowingEvent(
                start=pending.start,
                seeds=pending.seeds,
                direction=pending.direction,
                placement_mode=pending.placement_mode,
                path=path,
                landing_pit=landing_pit,
                board_after_sowing=tuple(board),
                capture_triggered=False,
            )
        )
        relay_seeds = board[landing_pit]
        board[landing_pit] = 0
        pending = PendingSowing(
            board=tuple(board),
            start=landing_pit,
            seeds=relay_seeds,
            direction=pending.direction,
            placement_mode=PlacementMode.NEXT_PIT,
        )


def winner(state: GameState) -> Player | None:
    front_row_winner = _winner_if_front_row_empty(state.pits)
    if front_row_winner is not None:
        return front_row_winner
    if legal_moves(state):
        return None
    return state.to_move.opponent


def rotate_180_and_swap_players(state: GameState) -> GameState:
    pits = state.pits
    rotated = (
        tuple(reversed(pits[16:24]))
        + tuple(reversed(pits[24:32]))
        + tuple(reversed(pits[0:8]))
        + tuple(reversed(pits[8:16]))
    )
    return GameState(rotated, state.to_move.opponent)


def reflect_columns(state: GameState) -> GameState:
    pits = state.pits
    reflected = (
        tuple(reversed(pits[0:8]))
        + tuple(reversed(pits[8:16]))
        + tuple(reversed(pits[16:24]))
        + tuple(reversed(pits[24:32]))
    )
    return GameState(reflected, state.to_move)


def canonical_key(state: GameState) -> tuple[int, ...]:
    player_perspective = state if state.to_move is Player.SOUTH else rotate_180_and_swap_players(state)
    reflected = reflect_columns(player_perspective)
    return min(player_perspective.pits, reflected.pits)


def state_from_rows(
    south_inner: tuple[int, ...] | list[int],
    south_outer: tuple[int, ...] | list[int],
    north_inner: tuple[int, ...] | list[int],
    north_outer: tuple[int, ...] | list[int],
    *,
    to_move: Player,
) -> GameState:
    rows = tuple(int(value) for value in south_inner + south_outer + north_inner + north_outer)  # type: ignore[operator]
    return GameState(rows, to_move)


def _validate_move_shape(state: GameState, move: Move) -> None:
    if not belongs_to_player(move.start, state.to_move):
        raise ValueError("The starting pit must belong to the player to move.")


def _classify_move_kind(state: GameState, move: Move) -> MoveKind:
    capture_starts = _capture_start_moves(state)
    if capture_starts:
        if move not in capture_starts:
            raise ValueError("A capture is available, so the move must be mtaji.")
        return MoveKind.MTAJI

    takasa_candidates = _takasa_candidates(state)
    if move not in takasa_candidates:
        raise ValueError("The move is not a pseudo-legal takasa candidate.")
    return MoveKind.TAKASA


def _capture_start_moves(state: GameState) -> list[Move]:
    moves: list[Move] = []
    for start in _player_pits(state.to_move):
        seeds = state.pits[start]
        if seeds < 2 or seeds >= 16:
            continue
        for direction in Direction:
            move = Move(start, direction)
            preview = preview_first_sowing(state, move)
            if preview.capture_possible:
                moves.append(move)
    return moves


def _takasa_candidates(state: GameState) -> list[Move]:
    inner_starts = [pit for pit in PLAYER_ROWS[state.to_move][ROW_INNER] if state.pits[pit] >= 2]
    allowed_starts = inner_starts if inner_starts else [pit for pit in PLAYER_ROWS[state.to_move][ROW_OUTER] if state.pits[pit] >= 2]

    filled_inner_pits = [pit for pit in PLAYER_ROWS[state.to_move][ROW_INNER] if state.pits[pit] > 0]
    lone_filled_inner_kichwa = len(filled_inner_pits) == 1 and is_kichwa(filled_inner_pits[0])

    moves: list[Move] = []
    for start in allowed_starts:
        for direction in Direction:
            if lone_filled_inner_kichwa and start == filled_inner_pits[0]:
                next_pit = NEXT_PIT[(state.to_move, direction, start)]
                if next_pit in PLAYER_ROWS[state.to_move][ROW_OUTER]:
                    continue
            moves.append(Move(start, direction))
    return moves


def _player_pits(player: Player) -> tuple[int, ...]:
    return PLAYER_ROWS[player][ROW_INNER] + PLAYER_ROWS[player][ROW_OUTER]


def _opposite_inner_pit(index: int) -> int:
    if not is_inner_pit(index):
        raise ValueError("Only inner-row pits have opposites.")
    return pit_index(player_of_pit(index).opponent, ROW_INNER, column_of(index))


def _capture_restart(player: Player, capturing_pit: int, current_direction: Direction) -> tuple[int, Direction]:
    column = column_of(capturing_pit)
    if column in (1, 2):
        return pit_index(player, ROW_INNER, 1), Direction.CLOCKWISE
    if column in (7, 8):
        return pit_index(player, ROW_INNER, 8), Direction.ANTICLOCKWISE
    if current_direction is Direction.CLOCKWISE:
        return pit_index(player, ROW_INNER, 1), Direction.CLOCKWISE
    return pit_index(player, ROW_INNER, 8), Direction.ANTICLOCKWISE


def _sow(
    board: list[int],
    player: Player,
    start: int,
    seeds: int,
    direction: Direction,
    placement_mode: PlacementMode,
) -> tuple[tuple[int, ...], int, int, Player | None]:
    landing_pit = -1
    placed_count = 0
    path = pit_sequence(
        player,
        start,
        direction,
        seeds,
        include_start=placement_mode is PlacementMode.START_PIT,
    )
    for pit in path:
        board[pit] += 1
        landing_pit = pit
        placed_count += 1
        front_row_winner = _winner_if_front_row_empty(tuple(board))
        if front_row_winner is not None:
            return path, landing_pit, placed_count, front_row_winner
    return path, landing_pit, placed_count, None


def _winner_if_front_row_empty(pits: tuple[int, ...]) -> Player | None:
    if all(pits[pit] == 0 for pit in SOUTH_INNER):
        return Player.NORTH
    if all(pits[pit] == 0 for pit in NORTH_INNER):
        return Player.SOUTH
    return None


def _terminal_result(
    board: list[int],
    mover: Player,
    move_kind: MoveKind,
    *,
    sowings: int,
    seeds_sown: int,
    winner: Player,
    trace: tuple[SowingEvent, ...],
) -> MoveResult:
    termination = (
        MoveTermination.OPPONENT_FRONT_ROW_EMPTY
        if winner is mover
        else MoveTermination.CURRENT_PLAYER_FRONT_ROW_EMPTY
    )
    snapshot = tuple(board)
    return MoveResult(
        state=GameState(snapshot, mover.opponent) if sum(snapshot) == 64 else None,
        move_kind=move_kind,
        sowings=sowings,
        seeds_sown=seeds_sown,
        board_snapshot=snapshot,
        trace=trace,
        terminal_winner=winner,
        termination=termination,
    )
