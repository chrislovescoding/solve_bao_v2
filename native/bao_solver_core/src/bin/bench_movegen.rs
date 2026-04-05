use std::fs::File;
use std::hint::black_box;
use std::io::{BufRead, BufReader};
use std::path::{Path, PathBuf};
use std::time::Instant;

use bao_solver_core::{apply_move, legal_moves, Direction, MoveCode, Player, StateWork};
use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize)]
struct CorpusMove {
    move_start: u8,
    move_direction: String,
}

#[derive(Debug, Deserialize)]
struct CorpusRecord {
    state: Vec<u8>,
    to_move: String,
    legal_moves: Vec<CorpusMove>,
}

#[derive(Debug, Serialize)]
struct KernelReport {
    name: &'static str,
    total_ops: usize,
    elapsed_ns: u128,
    ns_per_op: f64,
    ops_per_sec: f64,
    checksum_hex: String,
}

#[derive(Debug, Serialize)]
struct BenchmarkReport {
    benchmark: &'static str,
    profile: &'static str,
    corpus_path: String,
    states: usize,
    legal_move_pairs: usize,
    warmup_iterations: usize,
    measured_iterations: usize,
    legal_moves: KernelReport,
    apply_move: KernelReport,
}

fn parse_player(name: &str) -> Result<Player, String> {
    match name {
        "south" => Ok(Player::South),
        "north" => Ok(Player::North),
        other => Err(format!("unknown player name: {other}")),
    }
}

fn parse_direction(name: &str) -> Result<Direction, String> {
    match name {
        "clockwise" => Ok(Direction::Clockwise),
        "anti_clockwise" => Ok(Direction::Anticlockwise),
        other => Err(format!("unknown direction name: {other}")),
    }
}

fn load_corpus(path: &Path) -> Result<(Vec<StateWork>, Vec<(StateWork, MoveCode)>), String> {
    let handle = File::open(path).map_err(|err| format!("failed to open {}: {err}", path.display()))?;
    let reader = BufReader::new(handle);
    let mut states = Vec::new();
    let mut move_pairs = Vec::new();

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
        states.push(state);

        for mv in &record.legal_moves {
            let direction = parse_direction(&mv.move_direction)?;
            move_pairs.push((
                state,
                MoveCode::new(mv.move_start, direction)
                    .ok_or_else(|| format!("line {} contains invalid move start {}", line_number + 1, mv.move_start))?,
            ));
        }
    }

    if states.is_empty() {
        return Err("benchmark corpus must contain at least one state".to_string());
    }
    if move_pairs.is_empty() {
        return Err("benchmark corpus must contain at least one legal move".to_string());
    }

    Ok((states, move_pairs))
}

fn mix_checksum(current: u128, value: u128) -> u128 {
    current
        .rotate_left(11)
        .wrapping_add(value ^ 0x9e37_79b9_7f4a_7c15_6c8e_9cf5_7093_d5a1u128)
}

fn legal_moves_checksum_value(moves: &[MoveCode]) -> u128 {
    let mut value = 0u128;
    for mv in moves {
        value = value.rotate_left(5).wrapping_add(mv.raw() as u128);
    }
    value
}

fn apply_move_checksum_value(result: &bao_solver_core::MoveResult) -> u128 {
    let mut value = 0u128;
    for (index, pit) in result.board_snapshot.iter().enumerate() {
        value = value.rotate_left(3).wrapping_add((*pit as u128) << (index % 8));
    }
    value = value.rotate_left(7).wrapping_add(result.sowings as u128);
    value = value.rotate_left(7).wrapping_add(result.seeds_sown as u128);
    value = value.rotate_left(7).wrapping_add(result.captures as u128);
    value = value.rotate_left(1).wrapping_add(result.infinite_move as u128);
    value
}

fn warmup_legal_moves(states: &[StateWork], iterations: usize) {
    let mut checksum = 0u128;
    for _ in 0..iterations {
        for state in states {
            let moves = black_box(legal_moves(*state));
            checksum = mix_checksum(checksum, legal_moves_checksum_value(&moves));
        }
    }
    black_box(checksum);
}

fn warmup_apply_move(move_pairs: &[(StateWork, MoveCode)], iterations: usize) -> Result<(), String> {
    let mut checksum = 0u128;
    for _ in 0..iterations {
        for (state, mv) in move_pairs {
            let result = black_box(apply_move(*state, *mv, false)?);
            checksum = mix_checksum(checksum, apply_move_checksum_value(&result));
        }
    }
    black_box(checksum);
    Ok(())
}

fn measure_legal_moves(states: &[StateWork], iterations: usize) -> KernelReport {
    let total_ops = states.len() * iterations;
    let mut checksum = 0u128;
    let started = Instant::now();
    for _ in 0..iterations {
        for state in states {
            let moves = black_box(legal_moves(*state));
            checksum = mix_checksum(checksum, legal_moves_checksum_value(&moves));
        }
    }
    let elapsed_ns = started.elapsed().as_nanos();
    KernelReport {
        name: "legal_moves",
        total_ops,
        elapsed_ns,
        ns_per_op: elapsed_ns as f64 / total_ops as f64,
        ops_per_sec: (total_ops as f64 * 1_000_000_000.0) / elapsed_ns as f64,
        checksum_hex: format!("{checksum:032x}"),
    }
}

fn measure_apply_move(move_pairs: &[(StateWork, MoveCode)], iterations: usize) -> Result<KernelReport, String> {
    let total_ops = move_pairs.len() * iterations;
    let mut checksum = 0u128;
    let started = Instant::now();
    for _ in 0..iterations {
        for (state, mv) in move_pairs {
            let result = black_box(apply_move(*state, *mv, false)?);
            checksum = mix_checksum(checksum, apply_move_checksum_value(&result));
        }
    }
    let elapsed_ns = started.elapsed().as_nanos();
    Ok(KernelReport {
        name: "apply_move",
        total_ops,
        elapsed_ns,
        ns_per_op: elapsed_ns as f64 / total_ops as f64,
        ops_per_sec: (total_ops as f64 * 1_000_000_000.0) / elapsed_ns as f64,
        checksum_hex: format!("{checksum:032x}"),
    })
}

fn parse_arg_usize(payload: &str, label: &str) -> Result<usize, String> {
    payload
        .parse::<usize>()
        .map_err(|err| format!("invalid {label} value {payload}: {err}"))
}

fn main() -> Result<(), String> {
    let mut args = std::env::args().skip(1);
    let mut corpus = PathBuf::from("artifacts/reference_corpus_depth3.jsonl");
    let mut warmup_iterations = 500usize;
    let mut measured_iterations = 20_000usize;

    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--corpus" => {
                let value = args
                    .next()
                    .ok_or_else(|| "expected path after --corpus".to_string())?;
                corpus = PathBuf::from(value);
            }
            "--warmup-iterations" => {
                let value = args
                    .next()
                    .ok_or_else(|| "expected integer after --warmup-iterations".to_string())?;
                warmup_iterations = parse_arg_usize(&value, "warmup_iterations")?;
            }
            "--iterations" => {
                let value = args
                    .next()
                    .ok_or_else(|| "expected integer after --iterations".to_string())?;
                measured_iterations = parse_arg_usize(&value, "iterations")?;
            }
            other => return Err(format!("unknown argument: {other}")),
        }
    }

    let (states, move_pairs) = load_corpus(&corpus)?;
    warmup_legal_moves(&states, warmup_iterations);
    warmup_apply_move(&move_pairs, warmup_iterations)?;

    let report = BenchmarkReport {
        benchmark: "movegen",
        profile: if cfg!(debug_assertions) { "debug" } else { "release" },
        corpus_path: corpus.display().to_string(),
        states: states.len(),
        legal_move_pairs: move_pairs.len(),
        warmup_iterations,
        measured_iterations,
        legal_moves: measure_legal_moves(&states, measured_iterations),
        apply_move: measure_apply_move(&move_pairs, measured_iterations)?,
    };

    let payload = serde_json::to_string_pretty(&report)
        .map_err(|err| format!("failed to serialize benchmark report: {err}"))?;
    println!("{payload}");
    Ok(())
}
