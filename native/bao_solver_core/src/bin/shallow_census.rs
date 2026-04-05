use std::collections::HashSet;
use std::time::Instant;

use bao_solver_core::{apply_move, initial_state, legal_moves, MoveKind};
use serde::Serialize;

#[derive(Debug, Serialize)]
struct LayerMetrics {
    depth: usize,
    states: usize,
    canonical_states: usize,
    avg_branching: f64,
    moves: usize,
    avg_sowings: f64,
    mtaji: usize,
    takasa: usize,
    terminals: usize,
}

#[derive(Debug, Serialize)]
struct CensusReport {
    benchmark: &'static str,
    profile: &'static str,
    max_depth: usize,
    elapsed_ns: u128,
    layers: Vec<LayerMetrics>,
    total_unique_states: usize,
    canonical_unique_states: usize,
    canonical_reduction_factor: f64,
    terminal_results_encountered: usize,
    overall_avg_branching: f64,
    overall_avg_sowings: f64,
    overall_max_sowings: u32,
    mtaji_avg_sowings: f64,
    mtaji_max_sowings: u32,
    takasa_avg_sowings: f64,
    takasa_max_sowings: u32,
}

fn main() -> Result<(), String> {
    let mut args = std::env::args().skip(1);
    let mut depth = 6usize;

    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--depth" => {
                let value = args
                    .next()
                    .ok_or_else(|| "expected integer after --depth".to_string())?;
                depth = value
                    .parse::<usize>()
                    .map_err(|err| format!("invalid depth value {value}: {err}"))?;
            }
            other => return Err(format!("unknown argument: {other}")),
        }
    }

    let started = Instant::now();
    let initial = initial_state();
    let mut current = vec![initial];
    let mut discovered = HashSet::from([initial]);
    let mut discovered_canonical = HashSet::from([initial.pack_key()]);
    let mut layers = Vec::new();

    let mut overall_branching_sum = 0usize;
    let mut overall_branching_count = 0usize;
    let mut overall_sowings_sum = 0u64;
    let mut overall_sowings_count = 0usize;
    let mut overall_max_sowings = 0u32;
    let mut mtaji_sowings_sum = 0u64;
    let mut mtaji_sowings_count = 0usize;
    let mut mtaji_max_sowings = 0u32;
    let mut takasa_sowings_sum = 0u64;
    let mut takasa_sowings_count = 0usize;
    let mut takasa_max_sowings = 0u32;
    let mut terminal_results = 0usize;

    for current_depth in 0..depth {
        let mut next_layer = HashSet::new();
        let layer_canonical: HashSet<_> = current.iter().map(|state| state.pack_key()).collect();
        let mut layer_branching_sum = 0usize;
        let mut layer_move_count = 0usize;
        let mut layer_sowings_sum = 0u64;
        let mut layer_mtaji = 0usize;
        let mut layer_takasa = 0usize;
        let mut layer_terminals = 0usize;

        for state in &current {
            let moves = legal_moves(*state);
            let branching = moves.len();
            layer_branching_sum += branching;
            overall_branching_sum += branching;
            overall_branching_count += 1;
            layer_move_count += branching;

            for mv in moves {
                let result = apply_move(*state, mv, false)?;
                layer_sowings_sum += result.sowings as u64;
                overall_sowings_sum += result.sowings as u64;
                overall_sowings_count += 1;
                overall_max_sowings = overall_max_sowings.max(result.sowings);

                match result.move_kind {
                    MoveKind::Mtaji => {
                        layer_mtaji += 1;
                        mtaji_sowings_sum += result.sowings as u64;
                        mtaji_sowings_count += 1;
                        mtaji_max_sowings = mtaji_max_sowings.max(result.sowings);
                    }
                    MoveKind::Takasa => {
                        layer_takasa += 1;
                        takasa_sowings_sum += result.sowings as u64;
                        takasa_sowings_count += 1;
                        takasa_max_sowings = takasa_max_sowings.max(result.sowings);
                    }
                }

                if result.terminal_winner.is_some() {
                    layer_terminals += 1;
                    terminal_results += 1;
                    continue;
                }

                if let Some(next_state) = result.state {
                    if discovered.insert(next_state) {
                        discovered_canonical.insert(next_state.pack_key());
                        next_layer.insert(next_state);
                    }
                }
            }
        }

        layers.push(LayerMetrics {
            depth: current_depth,
            states: current.len(),
            canonical_states: layer_canonical.len(),
            avg_branching: if current.is_empty() {
                0.0
            } else {
                layer_branching_sum as f64 / current.len() as f64
            },
            moves: layer_move_count,
            avg_sowings: if layer_move_count == 0 {
                0.0
            } else {
                layer_sowings_sum as f64 / layer_move_count as f64
            },
            mtaji: layer_mtaji,
            takasa: layer_takasa,
            terminals: layer_terminals,
        });

        current = next_layer.into_iter().collect();
    }

    let report = CensusReport {
        benchmark: "shallow_census",
        profile: if cfg!(debug_assertions) { "debug" } else { "release" },
        max_depth: depth,
        elapsed_ns: started.elapsed().as_nanos(),
        layers,
        total_unique_states: discovered.len(),
        canonical_unique_states: discovered_canonical.len(),
        canonical_reduction_factor: if discovered_canonical.is_empty() {
            0.0
        } else {
            discovered.len() as f64 / discovered_canonical.len() as f64
        },
        terminal_results_encountered: terminal_results,
        overall_avg_branching: if overall_branching_count == 0 {
            0.0
        } else {
            overall_branching_sum as f64 / overall_branching_count as f64
        },
        overall_avg_sowings: if overall_sowings_count == 0 {
            0.0
        } else {
            overall_sowings_sum as f64 / overall_sowings_count as f64
        },
        overall_max_sowings,
        mtaji_avg_sowings: if mtaji_sowings_count == 0 {
            0.0
        } else {
            mtaji_sowings_sum as f64 / mtaji_sowings_count as f64
        },
        mtaji_max_sowings,
        takasa_avg_sowings: if takasa_sowings_count == 0 {
            0.0
        } else {
            takasa_sowings_sum as f64 / takasa_sowings_count as f64
        },
        takasa_max_sowings,
    };

    let payload = serde_json::to_string_pretty(&report)
        .map_err(|err| format!("failed to serialize census report: {err}"))?;
    println!("{payload}");
    Ok(())
}
