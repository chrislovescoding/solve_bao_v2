use std::fs::File;
use std::io::{BufRead, BufReader};
use std::path::PathBuf;

use bao_solver_core::{legal_moves, Player, StateWork};
use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize)]
struct CorpusRecord {
    state: Vec<u8>,
    to_move: String,
}

#[derive(Debug, Serialize)]
struct LegalMovesRecord {
    line_number: usize,
    legal_moves: Vec<u8>,
}

fn parse_player(name: &str) -> Result<Player, String> {
    match name {
        "south" => Ok(Player::South),
        "north" => Ok(Player::North),
        other => Err(format!("unknown player name: {other}")),
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
        let mut moves = legal_moves(state)
            .into_iter()
            .map(|mv| mv.raw())
            .collect::<Vec<_>>();
        moves.sort_unstable();

        let payload = serde_json::to_string(&LegalMovesRecord {
            line_number: line_number + 1,
            legal_moves: moves,
        })
        .map_err(|err| format!("failed to serialize output on line {}: {err}", line_number + 1))?;
        println!("{payload}");
    }

    Ok(())
}
