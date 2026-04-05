use std::fs::File;
use std::io::{BufRead, BufReader};
use std::path::PathBuf;

use bao_solver_core::{apply_move, legal_moves, Player, StateWork};
use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize)]
struct CorpusRecord {
    state: Vec<u8>,
    to_move: String,
}

#[derive(Debug, Serialize)]
struct SuccessorSummary {
    move_code: u8,
    move_kind: &'static str,
    sowings: u32,
    seeds_sown: u32,
    captures: u32,
    infinite_move: bool,
    terminal_winner: Option<&'static str>,
    termination: Option<&'static str>,
    board_snapshot: [u8; 32],
    result_to_move: Option<&'static str>,
    result_state_key_hex: Option<String>,
}

#[derive(Debug, Serialize)]
struct SuccessorRecord {
    line_number: usize,
    successors: Vec<SuccessorSummary>,
}

fn parse_player(name: &str) -> Result<Player, String> {
    match name {
        "south" => Ok(Player::South),
        "north" => Ok(Player::North),
        other => Err(format!("unknown player name: {other}")),
    }
}

fn player_name(player: Player) -> &'static str {
    match player {
        Player::South => "south",
        Player::North => "north",
    }
}

fn move_kind_name(kind: bao_solver_core::MoveKind) -> &'static str {
    match kind {
        bao_solver_core::MoveKind::Mtaji => "mtaji",
        bao_solver_core::MoveKind::Takasa => "takasa",
    }
}

fn termination_name(termination: bao_solver_core::MoveTermination) -> &'static str {
    match termination {
        bao_solver_core::MoveTermination::LandedInEmpty => "landed_in_empty",
        bao_solver_core::MoveTermination::CurrentPlayerFrontRowEmpty => "current_player_front_row_empty",
        bao_solver_core::MoveTermination::OpponentFrontRowEmpty => "opponent_front_row_empty",
        bao_solver_core::MoveTermination::InfiniteMove => "infinite_move",
    }
}

fn main() -> Result<(), String> {
    let path = std::env::args()
        .nth(1)
        .map(PathBuf::from)
        .ok_or_else(|| "expected path to reference corpus JSONL".to_string())?;

    let handle = File::open(&path).map_err(|err| format!("failed to open {}: {err}", path.display()))?;
    let reader = BufReader::new(handle);

    for (line_number, line) in reader.lines().enumerate() {
        let line = line.map_err(|err| format!("failed reading line {}: {err}", line_number + 1))?;
        if line.trim().is_empty() {
            continue;
        }

        let record: CorpusRecord =
            serde_json::from_str(&line).map_err(|err| format!("invalid JSON on line {}: {err}", line_number + 1))?;
        if record.state.len() != 32 {
            return Err(format!(
                "line {} expected 32 pits, got {}",
                line_number + 1,
                record.state.len()
            ));
        }

        let pits: [u8; 32] = record
            .state
            .try_into()
            .map_err(|_| format!("line {} failed converting pit vector to fixed array", line_number + 1))?;
        let player = parse_player(&record.to_move)?;
        let state = StateWork::new(pits, player)
            .ok_or_else(|| format!("line {} contains invalid state seed total", line_number + 1))?;

        let mut moves = legal_moves(state);
        moves.sort_unstable_by_key(|mv| mv.raw());

        let mut successors = Vec::with_capacity(moves.len());
        for mv in moves {
            let result = apply_move(state, mv, true)?;
            let (result_to_move, result_state_key_hex) = match result.state {
                Some(next_state) => (
                    Some(player_name(next_state.to_move)),
                    Some(format!("{:032x}", next_state.pack_key().0)),
                ),
                None => (None, None),
            };

            successors.push(SuccessorSummary {
                move_code: mv.raw(),
                move_kind: move_kind_name(result.move_kind),
                sowings: result.sowings,
                seeds_sown: result.seeds_sown,
                captures: result.captures,
                infinite_move: result.infinite_move,
                terminal_winner: result.terminal_winner.map(player_name),
                termination: result.termination.map(termination_name),
                board_snapshot: result.board_snapshot,
                result_to_move,
                result_state_key_hex,
            });
        }

        let payload = serde_json::to_string(&SuccessorRecord {
            line_number: line_number + 1,
            successors,
        })
        .map_err(|err| format!("failed to serialize output on line {}: {err}", line_number + 1))?;
        println!("{payload}");
    }

    Ok(())
}
