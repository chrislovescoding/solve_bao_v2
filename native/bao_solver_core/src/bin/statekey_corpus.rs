use std::fs::File;
use std::io::{BufRead, BufReader};
use std::path::PathBuf;

use bao_solver_core::{Player, StateWork};
use serde::Deserialize;

#[derive(Debug, Deserialize)]
struct CorpusRecord {
    canonical_state_key_hex: String,
    state: Vec<u8>,
    to_move: String,
}

fn parse_player(name: &str) -> Result<Player, String> {
    match name {
        "south" => Ok(Player::South),
        "north" => Ok(Player::North),
        other => Err(format!("unknown player name: {other}")),
    }
}

fn parse_hex_u128(payload: &str) -> Result<u128, String> {
    u128::from_str_radix(payload, 16).map_err(|err| format!("invalid hex key {payload}: {err}"))
}

fn main() -> Result<(), String> {
    let path = std::env::args()
        .nth(1)
        .map(PathBuf::from)
        .ok_or_else(|| "expected path to reference corpus JSONL".to_string())?;

    let handle = File::open(&path).map_err(|err| format!("failed to open {}: {err}", path.display()))?;
    let reader = BufReader::new(handle);

    let mut count = 0usize;
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
        let actual_key = state.pack_key().0;
        let expected_key = parse_hex_u128(&record.canonical_state_key_hex)?;

        if actual_key != expected_key {
            return Err(format!(
                "line {} state key mismatch: expected {:032x}, got {:032x}",
                line_number + 1,
                expected_key,
                actual_key
            ));
        }

        count += 1;
    }

    println!("validated_records={count}");
    println!("corpus_path={}", path.display());
    Ok(())
}
