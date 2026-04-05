use std::fs::File;
use std::hint::black_box;
use std::io::{BufRead, BufReader};
use std::path::{Path, PathBuf};
use std::time::Instant;

use bao_solver_core::{Player, StateKey, StateWork};
use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize)]
struct CorpusRecord {
    canonical_state_key_hex: String,
    state: Vec<u8>,
    to_move: String,
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
    records: usize,
    warmup_iterations: usize,
    measured_iterations: usize,
    pack_key: KernelReport,
    unpack_key: KernelReport,
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

fn load_corpus(path: &Path) -> Result<(Vec<StateWork>, Vec<StateKey>), String> {
    let handle = File::open(path).map_err(|err| format!("failed to open {}: {err}", path.display()))?;
    let reader = BufReader::new(handle);
    let mut states = Vec::new();
    let mut keys = Vec::new();

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
        let key = StateKey(parse_hex_u128(&record.canonical_state_key_hex)?);

        states.push(state);
        keys.push(key);
    }

    if states.is_empty() {
        return Err("benchmark corpus must contain at least one state".to_string());
    }

    Ok((states, keys))
}

fn warmup_pack(states: &[StateWork], iterations: usize) {
    let mut checksum = 0u128;
    for _ in 0..iterations {
        for state in states {
            checksum = mix_checksum(checksum, black_box(state.pack_key().0));
        }
    }
    black_box(checksum);
}

fn warmup_unpack(keys: &[StateKey], iterations: usize) {
    let mut checksum = 0u128;
    for _ in 0..iterations {
        for key in keys {
            let state = black_box(StateWork::from_key(*key));
            checksum = mix_checksum(checksum, unpack_checksum_value(&state));
        }
    }
    black_box(checksum);
}

fn mix_checksum(current: u128, value: u128) -> u128 {
    current
        .rotate_left(11)
        .wrapping_add(value ^ 0x9e37_79b9_7f4a_7c15_6c8e_9cf5_7093_d5a1u128)
}

fn unpack_checksum_value(state: &StateWork) -> u128 {
    let mut value = 0u128;
    for (index, pit) in state.pits.iter().enumerate() {
        value = value.rotate_left(3).wrapping_add((*pit as u128) << (index % 8));
    }
    value
}

fn measure_pack(states: &[StateWork], iterations: usize) -> KernelReport {
    let total_ops = states.len() * iterations;
    let mut checksum = 0u128;
    let started = Instant::now();
    for _ in 0..iterations {
        for state in states {
            checksum = mix_checksum(checksum, black_box(state.pack_key().0));
        }
    }
    let elapsed = started.elapsed();
    let elapsed_ns = elapsed.as_nanos();

    KernelReport {
        name: "pack_key",
        total_ops,
        elapsed_ns,
        ns_per_op: elapsed_ns as f64 / total_ops as f64,
        ops_per_sec: (total_ops as f64 * 1_000_000_000.0) / elapsed_ns as f64,
        checksum_hex: format!("{checksum:032x}"),
    }
}

fn measure_unpack(keys: &[StateKey], iterations: usize) -> KernelReport {
    let total_ops = keys.len() * iterations;
    let mut checksum = 0u128;
    let started = Instant::now();
    for _ in 0..iterations {
        for key in keys {
            let state = black_box(StateWork::from_key(*key));
            checksum = mix_checksum(checksum, unpack_checksum_value(&state));
        }
    }
    let elapsed = started.elapsed();
    let elapsed_ns = elapsed.as_nanos();

    KernelReport {
        name: "unpack_key",
        total_ops,
        elapsed_ns,
        ns_per_op: elapsed_ns as f64 / total_ops as f64,
        ops_per_sec: (total_ops as f64 * 1_000_000_000.0) / elapsed_ns as f64,
        checksum_hex: format!("{checksum:032x}"),
    }
}

fn parse_arg_usize(payload: &str, label: &str) -> Result<usize, String> {
    payload
        .parse::<usize>()
        .map_err(|err| format!("invalid {label} value {payload}: {err}"))
}

fn main() -> Result<(), String> {
    let mut args = std::env::args().skip(1);
    let mut corpus = PathBuf::from("artifacts/reference_corpus_depth2.jsonl");
    let mut warmup_iterations = 2_000usize;
    let mut measured_iterations = 200_000usize;

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
            other => {
                return Err(format!("unknown argument: {other}"));
            }
        }
    }

    if measured_iterations == 0 {
        return Err("measured iterations must be positive".to_string());
    }

    let (states, keys) = load_corpus(&corpus)?;
    warmup_pack(&states, warmup_iterations);
    warmup_unpack(&keys, warmup_iterations);

    let report = BenchmarkReport {
        benchmark: "statekey",
        profile: if cfg!(debug_assertions) { "debug" } else { "release" },
        corpus_path: corpus.display().to_string(),
        records: states.len(),
        warmup_iterations,
        measured_iterations,
        pack_key: measure_pack(&states, measured_iterations),
        unpack_key: measure_unpack(&keys, measured_iterations),
    };

    let payload = serde_json::to_string_pretty(&report)
        .map_err(|err| format!("failed to serialize benchmark report: {err}"))?;
    println!("{payload}");
    Ok(())
}
