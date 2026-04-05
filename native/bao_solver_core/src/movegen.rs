use std::collections::HashSet;

use crate::state::StateWork;
use crate::types::{Direction, MoveCode, MoveKind, MoveTermination, Player};

const SOUTH_INNER: [u8; 8] = [0, 1, 2, 3, 4, 5, 6, 7];
const SOUTH_OUTER: [u8; 8] = [8, 9, 10, 11, 12, 13, 14, 15];
const NORTH_INNER: [u8; 8] = [16, 17, 18, 19, 20, 21, 22, 23];
const NORTH_OUTER: [u8; 8] = [24, 25, 26, 27, 28, 29, 30, 31];

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
enum PlacementMode {
    StartPit,
    NextPit,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
struct PendingSowing {
    board: [u8; 32],
    start: u8,
    seeds: u8,
    direction: Direction,
    placement_mode: PlacementMode,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct FirstSowingPreview {
    pub landing_pit: u8,
    pub board_after_sowing: [u8; 32],
    pub capture_possible: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct MoveResult {
    pub state: Option<StateWork>,
    pub move_kind: MoveKind,
    pub sowings: u32,
    pub seeds_sown: u32,
    pub board_snapshot: [u8; 32],
    pub captures: u32,
    pub infinite_move: bool,
    pub terminal_winner: Option<Player>,
    pub termination: Option<MoveTermination>,
}

pub fn initial_state() -> StateWork {
    StateWork::new([2u8; 32], Player::South).expect("initial Bao state must be valid")
}

pub fn preview_first_sowing(state: StateWork, mv: MoveCode) -> Result<FirstSowingPreview, String> {
    validate_move_shape(state, mv)?;
    let start = mv.start() as usize;
    let seeds = state.pits[start];
    if seeds < 2 {
        return Err("the starting pit must contain at least 2 stones".to_string());
    }

    let mut board = state.pits;
    board[start] = 0;
    let (_, landing_pit, _, _) = sow(
        &mut board,
        state.to_move,
        mv.start(),
        seeds,
        mv.direction(),
        PlacementMode::NextPit,
    )?;

    let capture_possible = seeds < 16
        && is_inner_pit(landing_pit)
        && belongs_to_player(landing_pit, state.to_move)
        && board[landing_pit as usize] > 1
        && board[opposite_inner_pit(landing_pit)? as usize] > 0;

    Ok(FirstSowingPreview {
        landing_pit,
        board_after_sowing: board,
        capture_possible,
    })
}

pub fn legal_moves(state: StateWork) -> Vec<MoveCode> {
    if winner_if_front_row_empty(&state.pits).is_some() {
        return Vec::new();
    }

    let mut candidates = capture_start_moves(state);
    if candidates.is_empty() {
        candidates = takasa_candidates(state);
    }

    let mut finite_moves = Vec::with_capacity(candidates.len());
    for mv in candidates {
        if let Ok(result) = apply_move(state, mv, false) {
            if !result.infinite_move {
                finite_moves.push(mv);
            }
        }
    }
    finite_moves
}

pub fn has_legal_move(state: StateWork) -> bool {
    if winner_if_front_row_empty(&state.pits).is_some() {
        return false;
    }

    let capture_candidates = capture_start_moves(state);
    if !capture_candidates.is_empty() {
        return any_finite_candidate(state, &capture_candidates);
    }

    let takasa_candidates = takasa_candidates(state);
    any_finite_candidate(state, &takasa_candidates)
}

pub fn apply_move(state: StateWork, mv: MoveCode, validate: bool) -> Result<MoveResult, String> {
    let move_kind = classify_move_kind(state, mv)?;
    if validate && !legal_moves(state).contains(&mv) {
        return Err(format!(
            "illegal move: start={} direction={:?}",
            mv.start(),
            mv.direction()
        ));
    }

    let start = mv.start() as usize;
    let seeds = state.pits[start];
    if seeds < 2 {
        return Err("the starting pit must contain at least 2 stones".to_string());
    }

    let mut board = state.pits;
    board[start] = 0;
    let mut pending = PendingSowing {
        board,
        start: mv.start(),
        seeds,
        direction: mv.direction(),
        placement_mode: PlacementMode::NextPit,
    };
    let mut visited = HashSet::new();
    let mut sowings = 0u32;
    let mut seeds_sown = 0u32;
    let mut captures = 0u32;

    loop {
        if !visited.insert(pending) {
            return Ok(MoveResult {
                state: StateWork::new(pending.board, state.to_move.opponent()),
                move_kind,
                sowings,
                seeds_sown,
                board_snapshot: pending.board,
                captures,
                infinite_move: true,
                terminal_winner: None,
                termination: Some(MoveTermination::InfiniteMove),
            });
        }

        let mut board = pending.board;
        let (_, landing_pit, placed_count, front_row_winner) = sow(
            &mut board,
            state.to_move,
            pending.start,
            pending.seeds,
            pending.direction,
            pending.placement_mode,
        )?;
        sowings += 1;
        seeds_sown += placed_count as u32;

        if let Some(winner) = front_row_winner {
            return Ok(terminal_result(
                board,
                state.to_move,
                move_kind,
                sowings,
                seeds_sown,
                captures,
                winner,
            ));
        }

        if board[landing_pit as usize] == 1 {
            return Ok(MoveResult {
                state: StateWork::new(board, state.to_move.opponent()),
                move_kind,
                sowings,
                seeds_sown,
                board_snapshot: board,
                captures,
                infinite_move: false,
                terminal_winner: None,
                termination: Some(MoveTermination::LandedInEmpty),
            });
        }

        if move_kind == MoveKind::Mtaji
            && belongs_to_player(landing_pit, state.to_move)
            && is_inner_pit(landing_pit)
            && board[opposite_inner_pit(landing_pit)? as usize] > 0
        {
            let captured_pit = opposite_inner_pit(landing_pit)? as usize;
            let captured = board[captured_pit];
            board[captured_pit] = 0;
            captures += 1;

            if let Some(winner) = winner_if_front_row_empty(&board) {
                return Ok(terminal_result(
                    board,
                    state.to_move,
                    move_kind,
                    sowings,
                    seeds_sown,
                    captures,
                    winner,
                ));
            }

            let (capture_start, capture_direction) =
                capture_restart(state.to_move, landing_pit, pending.direction);
            pending = PendingSowing {
                board,
                start: capture_start,
                seeds: captured,
                direction: capture_direction,
                placement_mode: PlacementMode::StartPit,
            };
            continue;
        }

        let relay_seeds = board[landing_pit as usize];
        board[landing_pit as usize] = 0;
        pending = PendingSowing {
            board,
            start: landing_pit,
            seeds: relay_seeds,
            direction: pending.direction,
            placement_mode: PlacementMode::NextPit,
        };
    }
}

pub fn winner(state: StateWork) -> Option<Player> {
    if let Some(front_row_winner) = winner_if_front_row_empty(&state.pits) {
        return Some(front_row_winner);
    }
    if has_legal_move(state) {
        return None;
    }
    Some(state.to_move.opponent())
}

fn any_finite_candidate(state: StateWork, candidates: &[MoveCode]) -> bool {
    for mv in candidates {
        if let Ok(result) = apply_move(state, *mv, false) {
            if !result.infinite_move {
                return true;
            }
        }
    }
    false
}

fn validate_move_shape(state: StateWork, mv: MoveCode) -> Result<(), String> {
    if !belongs_to_player(mv.start(), state.to_move) {
        return Err("the starting pit must belong to the player to move".to_string());
    }
    Ok(())
}

fn classify_move_kind(state: StateWork, mv: MoveCode) -> Result<MoveKind, String> {
    let capture_starts = capture_start_moves(state);
    if !capture_starts.is_empty() {
        if !capture_starts.contains(&mv) {
            return Err("a capture is available, so the move must be mtaji".to_string());
        }
        return Ok(MoveKind::Mtaji);
    }

    let takasa = takasa_candidates(state);
    if !takasa.contains(&mv) {
        return Err("the move is not a pseudo-legal takasa candidate".to_string());
    }
    Ok(MoveKind::Takasa)
}

fn capture_start_moves(state: StateWork) -> Vec<MoveCode> {
    let mut moves = Vec::new();
    for start in player_pits(state.to_move) {
        let seeds = state.pits[start as usize];
        if !(2..16).contains(&seeds) {
            continue;
        }
        for direction in [Direction::Clockwise, Direction::Anticlockwise] {
            let mv = MoveCode::new(start, direction).expect("player pit must be encodable");
            if let Ok(preview) = preview_first_sowing(state, mv) {
                if preview.capture_possible {
                    moves.push(mv);
                }
            }
        }
    }
    moves
}

fn takasa_candidates(state: StateWork) -> Vec<MoveCode> {
    let inner_row = inner_row(state.to_move);
    let outer_row = outer_row(state.to_move);

    let inner_starts: Vec<u8> = inner_row
        .iter()
        .copied()
        .filter(|pit| state.pits[*pit as usize] >= 2)
        .collect();
    let allowed_starts = if inner_starts.is_empty() {
        outer_row
            .iter()
            .copied()
            .filter(|pit| state.pits[*pit as usize] >= 2)
            .collect::<Vec<_>>()
    } else {
        inner_starts
    };

    let filled_inner_pits: Vec<u8> = inner_row
        .iter()
        .copied()
        .filter(|pit| state.pits[*pit as usize] > 0)
        .collect();
    let lone_filled_inner_kichwa =
        filled_inner_pits.len() == 1 && is_kichwa(filled_inner_pits[0]);

    let mut moves = Vec::new();
    for start in allowed_starts {
        for direction in [Direction::Clockwise, Direction::Anticlockwise] {
            if lone_filled_inner_kichwa && start == filled_inner_pits[0] {
                let next = next_pit(state.to_move, direction, start).expect("next pit must exist");
                if outer_row.contains(&next) {
                    continue;
                }
            }
            moves.push(MoveCode::new(start, direction).expect("start pit must be encodable"));
        }
    }
    moves
}

fn sow(
    board: &mut [u8; 32],
    player: Player,
    start: u8,
    seeds: u8,
    direction: Direction,
    placement_mode: PlacementMode,
) -> Result<(u8, u8, u8, Option<Player>), String> {
    let mut landing_pit = 0u8;
    let mut current = if placement_mode == PlacementMode::StartPit {
        start
    } else {
        next_pit(player, direction, start)?
    };

    for placed_count in 1..=seeds {
        board[current as usize] = board[current as usize].saturating_add(1);
        landing_pit = current;
        if let Some(winner) = winner_if_front_row_empty(board) {
            return Ok((start, landing_pit, placed_count, Some(winner)));
        }
        current = next_pit(player, direction, current)?;
    }
    Ok((start, landing_pit, seeds, None))
}

fn terminal_result(
    board: [u8; 32],
    mover: Player,
    move_kind: MoveKind,
    sowings: u32,
    seeds_sown: u32,
    captures: u32,
    winner: Player,
) -> MoveResult {
    let termination = if winner == mover {
        MoveTermination::OpponentFrontRowEmpty
    } else {
        MoveTermination::CurrentPlayerFrontRowEmpty
    };
    MoveResult {
        state: StateWork::new(board, mover.opponent()),
        move_kind,
        sowings,
        seeds_sown,
        board_snapshot: board,
        captures,
        infinite_move: false,
        terminal_winner: Some(winner),
        termination: Some(termination),
    }
}

fn winner_if_front_row_empty(pits: &[u8; 32]) -> Option<Player> {
    if SOUTH_INNER.iter().all(|pit| pits[*pit as usize] == 0) {
        return Some(Player::North);
    }
    if NORTH_INNER.iter().all(|pit| pits[*pit as usize] == 0) {
        return Some(Player::South);
    }
    None
}

fn belongs_to_player(index: u8, player: Player) -> bool {
    match player {
        Player::South => index < 16,
        Player::North => index >= 16,
    }
}

fn is_inner_pit(index: u8) -> bool {
    index < 8 || (16..24).contains(&index)
}

fn is_kichwa(index: u8) -> bool {
    is_inner_pit(index) && matches!(column_of(index), 1 | 8)
}

fn column_of(index: u8) -> u8 {
    (index % 8) + 1
}

fn pit_index(player: Player, inner: bool, column: u8) -> Result<u8, String> {
    if !(1..=8).contains(&column) {
        return Err(format!("column must be between 1 and 8, got {column}"));
    }
    let base = match (player, inner) {
        (Player::South, true) => 0,
        (Player::South, false) => 8,
        (Player::North, true) => 16,
        (Player::North, false) => 24,
    };
    Ok(base + (column - 1))
}

fn opposite_inner_pit(index: u8) -> Result<u8, String> {
    if !is_inner_pit(index) {
        return Err("only inner-row pits have opposites".to_string());
    }
    pit_index(owner_of(index).opponent(), true, column_of(index))
}

fn owner_of(index: u8) -> Player {
    if index < 16 {
        Player::South
    } else {
        Player::North
    }
}

fn capture_restart(player: Player, capturing_pit: u8, current_direction: Direction) -> (u8, Direction) {
    match column_of(capturing_pit) {
        1 | 2 => (pit_index(player, true, 1).expect("left kichwa must exist"), Direction::Clockwise),
        7 | 8 => (
            pit_index(player, true, 8).expect("right kichwa must exist"),
            Direction::Anticlockwise,
        ),
        _ if current_direction == Direction::Clockwise => (
            pit_index(player, true, 1).expect("left kichwa must exist"),
            Direction::Clockwise,
        ),
        _ => (
            pit_index(player, true, 8).expect("right kichwa must exist"),
            Direction::Anticlockwise,
        ),
    }
}

fn next_pit(player: Player, direction: Direction, pit: u8) -> Result<u8, String> {
    match (player, direction) {
        (Player::South, Direction::Clockwise) => match pit {
            0..=6 => Ok(pit + 1),
            7 => Ok(15),
            9..=15 => Ok(pit - 1),
            8 => Ok(0),
            _ => Err(format!("pit {pit} does not belong to south")),
        },
        (Player::South, Direction::Anticlockwise) => match pit {
            0 => Ok(8),
            8..=14 => Ok(pit + 1),
            15 => Ok(7),
            1..=7 => Ok(pit - 1),
            _ => Err(format!("pit {pit} does not belong to south")),
        },
        (Player::North, Direction::Clockwise) => match pit {
            16..=22 => Ok(pit + 1),
            23 => Ok(31),
            25..=31 => Ok(pit - 1),
            24 => Ok(16),
            _ => Err(format!("pit {pit} does not belong to north")),
        },
        (Player::North, Direction::Anticlockwise) => match pit {
            16 => Ok(24),
            24..=30 => Ok(pit + 1),
            31 => Ok(23),
            17..=23 => Ok(pit - 1),
            _ => Err(format!("pit {pit} does not belong to north")),
        },
    }
}

fn player_pits(player: Player) -> [u8; 16] {
    match player {
        Player::South => [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
        Player::North => [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31],
    }
}

fn inner_row(player: Player) -> &'static [u8; 8] {
    match player {
        Player::South => &SOUTH_INNER,
        Player::North => &NORTH_INNER,
    }
}

fn outer_row(player: Player) -> &'static [u8; 8] {
    match player {
        Player::South => &SOUTH_OUTER,
        Player::North => &NORTH_OUTER,
    }
}

#[cfg(test)]
mod tests {
    use super::{apply_move, initial_state, legal_moves, winner, Direction, MoveCode, MoveKind, MoveTermination, Player};
    use crate::state::StateWork;

    fn state_from_rows(
        south_inner: [u8; 8],
        south_outer: [u8; 8],
        north_inner: [u8; 8],
        north_outer: [u8; 8],
        to_move: Player,
    ) -> StateWork {
        let mut pits = [0u8; 32];
        pits[0..8].copy_from_slice(&south_inner);
        pits[8..16].copy_from_slice(&south_outer);
        pits[16..24].copy_from_slice(&north_inner);
        pits[24..32].copy_from_slice(&north_outer);
        StateWork::new(pits, to_move).expect("test state must be valid")
    }

    #[test]
    fn initial_state_has_expected_legal_moves() {
        let moves = legal_moves(initial_state());
        assert_eq!(moves.len(), 16);
        assert!(moves.contains(&MoveCode::new(0, Direction::Clockwise).unwrap()));
        assert!(!moves.contains(&MoveCode::new(0, Direction::Anticlockwise).unwrap()));
    }

    #[test]
    fn initial_clockwise_move_matches_reference_result() {
        let result = apply_move(
            initial_state(),
            MoveCode::new(0, Direction::Clockwise).unwrap(),
            true,
        )
        .unwrap();

        assert_eq!(result.move_kind, MoveKind::Mtaji);
        assert_eq!(result.sowings, 10);
        assert_eq!(result.captures, 4);
        assert_eq!(result.termination, Some(MoveTermination::LandedInEmpty));
        assert_eq!(
            result.board_snapshot,
            [3, 1, 0, 4, 4, 4, 1, 5, 3, 3, 0, 3, 3, 0, 3, 3, 2, 0, 0, 2, 2, 2, 0, 0, 2, 2, 2, 2, 2, 2, 2, 2]
        );
        assert_eq!(result.state.unwrap().to_move, Player::North);
    }

    #[test]
    fn takasa_uses_front_row_when_possible() {
        let state = state_from_rows(
            [0, 0, 2, 0, 0, 0, 0, 0],
            [2, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 1],
            [59, 0, 0, 0, 0, 0, 0, 0],
            Player::South,
        );

        let moves = legal_moves(state);
        assert!(!moves.is_empty());
        assert!(moves.iter().all(|mv| mv.start() == 2));
    }

    #[test]
    fn lone_kichwa_restriction_matches_reference() {
        let state = state_from_rows(
            [2, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 1],
            [61, 0, 0, 0, 0, 0, 0, 0],
            Player::South,
        );

        assert_eq!(
            legal_moves(state),
            vec![MoveCode::new(0, Direction::Clockwise).unwrap()]
        );
    }

    #[test]
    fn winner_reports_no_move_loss() {
        let state = state_from_rows(
            [1, 1, 1, 1, 1, 1, 1, 1],
            [1, 1, 1, 1, 1, 1, 1, 1],
            [2, 0, 0, 0, 0, 0, 0, 0],
            [46, 0, 0, 0, 0, 0, 0, 0],
            Player::South,
        );

        assert_eq!(winner(state), Some(Player::North));
    }
}
