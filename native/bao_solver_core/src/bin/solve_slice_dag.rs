use std::fs;
use std::io::{BufWriter, Write};
use std::path::PathBuf;
use std::time::Instant;

use serde_json::json;

const HEADER_BYTES: usize = 64;
const STATE_RECORD_BYTES: usize = 32;
const ADJ_RECORD_BYTES: usize = 12;
const OFFSET_BYTES: usize = 4;
const SOLUTION_RECORD_BYTES: usize = 8;
const TERMINAL_RESULT_ID: u32 = u32::MAX;
const UNKNOWN_DISTANCE: u32 = u32::MAX;
const UNKNOWN_MOVE_CODE: u8 = 0xFF;
const STATE_MAGIC: [u8; 8] = *b"BAOSTATE";
const ADJ_MAGIC: [u8; 8] = *b"BAOADJ!!";
const SOLUTION_MAGIC: [u8; 8] = *b"BAOSOLVE";

#[derive(Clone, Copy, PartialEq, Eq)]
enum Outcome {
    Win,
    Loss,
}

#[derive(Clone, Copy)]
enum MoveKind {
    Win,
    Loss,
    Unknown,
    Node(u32),
}

#[derive(Clone, Copy)]
struct SolverMove {
    move_code: u8,
    kind: MoveKind,
}

#[derive(Clone, Copy)]
struct StateRecord {
    expanded: bool,
    terminal_outcome: Option<Outcome>,
    terminal_distance: Option<u32>,
}

#[derive(Clone, Copy)]
struct SolutionRecord {
    outcome: Option<Outcome>,
    best_move_code: Option<u8>,
    distance: Option<u32>,
    partial: bool,
    terminal_seed: bool,
    frontier_dependent: bool,
}

fn read_u16(raw: &[u8], offset: usize) -> Result<u16, String> {
    let bytes: [u8; 2] = raw[offset..offset + 2].try_into().map_err(|_| "bad u16 slice".to_string())?;
    Ok(u16::from_le_bytes(bytes))
}

fn read_u32(raw: &[u8], offset: usize) -> Result<u32, String> {
    let bytes: [u8; 4] = raw[offset..offset + 4].try_into().map_err(|_| "bad u32 slice".to_string())?;
    Ok(u32::from_le_bytes(bytes))
}

fn read_u64(raw: &[u8], offset: usize) -> Result<u64, String> {
    let bytes: [u8; 8] = raw[offset..offset + 8].try_into().map_err(|_| "bad u64 slice".to_string())?;
    Ok(u64::from_le_bytes(bytes))
}

fn parse_header(raw: &[u8], magic: [u8; 8]) -> Result<(usize, usize, usize, String), String> {
    if raw.len() < HEADER_BYTES || raw[0..8] != magic {
        return Err("invalid shard header".to_string());
    }
    Ok((
        read_u16(raw, 14)? as usize,
        read_u64(raw, 16)? as usize,
        read_u64(raw, 32)? as usize,
        String::from_utf8_lossy(&raw[40..64]).trim_end_matches('\0').to_string(),
    ))
}

fn parse_states(raw: &[u8], count: usize) -> Result<Vec<StateRecord>, String> {
    let mut states = Vec::with_capacity(count);
    for local_id in 0..count {
        let offset = HEADER_BYTES + local_id * STATE_RECORD_BYTES;
        let flags = raw[offset + 17];
        let terminal_outcome = match raw[offset + 18] {
            1 => Some(Outcome::Win),
            2 => Some(Outcome::Loss),
            _ => None,
        };
        let terminal_distance = if raw[offset + 19] == 0xFF {
            None
        } else {
            Some(raw[offset + 19] as u32)
        };
        states.push(StateRecord {
            expanded: (flags & 1) != 0,
            terminal_outcome,
            terminal_distance,
        });
    }
    Ok(states)
}

fn write_solution_shard(
    path: &PathBuf,
    records: &[SolutionRecord],
    depth: usize,
    resolved_count: usize,
    rulespec_version: &str,
) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|err| format!("failed creating solution dir: {err}"))?;
    }
    let mut writer = BufWriter::new(fs::File::create(path).map_err(|err| format!("failed creating solution shard: {err}"))?);
    let payload_bytes = records.len() * SOLUTION_RECORD_BYTES;
    let mut header = [0u8; HEADER_BYTES];
    header[0..8].copy_from_slice(&SOLUTION_MAGIC);
    header[8..10].copy_from_slice(&(1u16).to_le_bytes());
    header[10..12].copy_from_slice(&(HEADER_BYTES as u16).to_le_bytes());
    header[12..14].copy_from_slice(&(SOLUTION_RECORD_BYTES as u16).to_le_bytes());
    header[14..16].copy_from_slice(&(depth as u16).to_le_bytes());
    header[16..24].copy_from_slice(&(records.len() as u64).to_le_bytes());
    header[24..32].copy_from_slice(&(payload_bytes as u64).to_le_bytes());
    header[32..40].copy_from_slice(&(resolved_count as u64).to_le_bytes());
    let version = rulespec_version.as_bytes();
    header[40..40 + version.len()].copy_from_slice(version);
    writer.write_all(&header).map_err(|err| format!("failed writing solution header: {err}"))?;
    for record in records {
        let outcome_code = match record.outcome {
            None => 0u8,
            Some(Outcome::Win) => 1u8,
            Some(Outcome::Loss) => 2u8,
        };
        let best_move_code = record.best_move_code.unwrap_or(UNKNOWN_MOVE_CODE);
        let distance = record.distance.unwrap_or(UNKNOWN_DISTANCE);
        let mut flags = 0u8;
        if record.partial {
            flags |= 1 << 0;
        }
        if record.terminal_seed {
            flags |= 1 << 1;
        }
        if record.frontier_dependent {
            flags |= 1 << 2;
        }
        let mut payload = [0u8; SOLUTION_RECORD_BYTES];
        payload[0] = outcome_code;
        payload[1] = best_move_code;
        payload[2..6].copy_from_slice(&distance.to_le_bytes());
        payload[6] = flags;
        writer.write_all(&payload).map_err(|err| format!("failed writing solution record: {err}"))?;
    }
    writer.flush().map_err(|err| format!("failed flushing solution shard: {err}"))?;
    Ok(())
}

fn run() -> Result<i32, String> {
    let started = Instant::now();
    let mut args = std::env::args().skip(1);
    let mut state_binary = PathBuf::new();
    let mut adjacency_binary = PathBuf::new();
    let mut graph_summary = PathBuf::new();
    let mut output = PathBuf::new();
    let mut solution_output = PathBuf::new();
    let mut scc_summary_output = PathBuf::new();
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--state-binary" => state_binary = PathBuf::from(args.next().ok_or_else(|| "missing --state-binary value".to_string())?),
            "--adjacency-binary" => adjacency_binary = PathBuf::from(args.next().ok_or_else(|| "missing --adjacency-binary value".to_string())?),
            "--graph-summary" => graph_summary = PathBuf::from(args.next().ok_or_else(|| "missing --graph-summary value".to_string())?),
            "--output" => output = PathBuf::from(args.next().ok_or_else(|| "missing --output value".to_string())?),
            "--solution-output" => solution_output = PathBuf::from(args.next().ok_or_else(|| "missing --solution-output value".to_string())?),
            "--scc-summary-output" => scc_summary_output = PathBuf::from(args.next().ok_or_else(|| "missing --scc-summary-output value".to_string())?),
            "--solution-manifest" => {
                let _ = args.next();
            }
            other => return Err(format!("unknown argument: {other}")),
        }
    }

    eprintln!("[solve_slice_dag] loading_shards");
    let state_raw = fs::read(&state_binary).map_err(|err| format!("failed reading state shard: {err}"))?;
    let adjacency_raw = fs::read(&adjacency_binary).map_err(|err| format!("failed reading adjacency shard: {err}"))?;
    let (depth, state_count, _, rulespec_version) = parse_header(&state_raw, STATE_MAGIC)?;
    let (_, edge_count, aux_count, _) = parse_header(&adjacency_raw, ADJ_MAGIC)?;
    if aux_count != state_count {
        return Err("state/adjacency count mismatch".to_string());
    }
    let states = parse_states(&state_raw, state_count)?;
    let expanded_local_ids: Vec<u32> = states
        .iter()
        .enumerate()
        .filter_map(|(i, state)| if state.expanded { Some(i as u32) } else { None })
        .collect();
    let expanded_count = expanded_local_ids.len();
    let mut dense_index_by_local = vec![u32::MAX; state_count];
    for (dense_index, local_id) in expanded_local_ids.iter().enumerate() {
        dense_index_by_local[*local_id as usize] = dense_index as u32;
    }

    let offset_table_start = HEADER_BYTES;
    let payload_start = HEADER_BYTES + (state_count + 1) * OFFSET_BYTES;
    let offsets: Vec<u32> = (0..=state_count)
        .map(|index| read_u32(&adjacency_raw, offset_table_start + index * OFFSET_BYTES))
        .collect::<Result<_, _>>()?;

    eprintln!("[solve_slice_dag] building_solver_graph expanded_states={expanded_count}");
    let build_step = usize::max(1, expanded_count / 20);
    let mut moves_by_node = Vec::with_capacity(expanded_count);
    let mut graph_edges = Vec::with_capacity(expanded_count);
    for (index, local_id) in expanded_local_ids.iter().enumerate() {
        let start = offsets[*local_id as usize] as usize;
        let end = offsets[*local_id as usize + 1] as usize;
        let mut moves = Vec::with_capacity(end - start);
        let mut targets = Vec::new();
        for edge_index in start..end {
            let offset = payload_start + edge_index * ADJ_RECORD_BYTES;
            let result_id = read_u32(&adjacency_raw, offset)?;
            let move_code = adjacency_raw[offset + 9];
            let flags = adjacency_raw[offset + 10];
            let kind = match (flags >> 5) & 0b11 {
                1 => MoveKind::Win,
                2 => MoveKind::Loss,
                _ if result_id == TERMINAL_RESULT_ID => MoveKind::Unknown,
                _ => {
                    let dense = dense_index_by_local[result_id as usize];
                    if dense == u32::MAX {
                        MoveKind::Unknown
                    } else {
                        targets.push(dense);
                        MoveKind::Node(dense)
                    }
                }
            };
            moves.push(SolverMove { move_code, kind });
        }
        moves_by_node.push(moves);
        graph_edges.push(targets);
        let built = index + 1;
        if built == expanded_count || built % build_step == 0 {
            eprintln!("[solve_slice_dag] solver_graph_progress built={built}/{expanded_count}");
        }
    }

    eprintln!("[solve_slice_dag] checking_dag");
    let mut indegree = vec![0u32; expanded_count];
    for targets in &graph_edges {
        for target in targets {
            indegree[*target as usize] += 1;
        }
    }
    let mut stack: Vec<u32> = indegree
        .iter()
        .enumerate()
        .filter_map(|(index, value)| if *value == 0 { Some(index as u32) } else { None })
        .collect();
    let mut topo = Vec::with_capacity(expanded_count);
    while let Some(node) = stack.pop() {
        topo.push(node);
        for target in &graph_edges[node as usize] {
            indegree[*target as usize] -= 1;
            if indegree[*target as usize] == 0 {
                stack.push(*target);
            }
        }
    }
    if topo.len() != expanded_count {
        eprintln!("[solve_slice_dag] cycle_detected expanded_states={expanded_count} dag_nodes={}", topo.len());
        return Ok(3);
    }

    eprintln!("[solve_slice_dag] solving_dag node_count={expanded_count}");
    let solve_step = usize::max(1, expanded_count / 20);
    let mut outcomes = vec![None; expanded_count];
    let mut distances = vec![None; expanded_count];
    let mut best_moves = vec![None; expanded_count];
    for (processed_index, node) in topo.iter().rev().enumerate() {
        let moves = &moves_by_node[*node as usize];
        if moves.is_empty() {
            outcomes[*node as usize] = Some(Outcome::Loss);
            distances[*node as usize] = Some(0);
        } else {
            let mut best_win: Option<(u32, u8)> = None;
            let mut best_loss: Option<(u32, u8)> = None;
            let mut unresolved = false;
            let mut losing_candidates = 0usize;
            for mv in moves {
                match mv.kind {
                    MoveKind::Win => {
                        let candidate = (1u32, mv.move_code);
                        if best_win.map_or(true, |current| candidate < current) {
                            best_win = Some(candidate);
                        }
                    }
                    MoveKind::Loss => {
                        losing_candidates += 1;
                        let candidate = (1u32, mv.move_code);
                        if best_loss.map_or(true, |current| candidate.0 > current.0 || (candidate.0 == current.0 && candidate.1 < current.1)) {
                            best_loss = Some(candidate);
                        }
                    }
                    MoveKind::Unknown => unresolved = true,
                    MoveKind::Node(target) => match outcomes[target as usize] {
                        Some(Outcome::Loss) => {
                            let candidate = (distances[target as usize].unwrap_or(0) + 1, mv.move_code);
                            if best_win.map_or(true, |current| candidate < current) {
                                best_win = Some(candidate);
                            }
                        }
                        Some(Outcome::Win) => {
                            losing_candidates += 1;
                            let candidate = (distances[target as usize].unwrap_or(0) + 1, mv.move_code);
                            if best_loss.map_or(true, |current| candidate.0 > current.0 || (candidate.0 == current.0 && candidate.1 < current.1)) {
                                best_loss = Some(candidate);
                            }
                        }
                        None => unresolved = true,
                    },
                }
            }
            if let Some((distance, move_code)) = best_win {
                outcomes[*node as usize] = Some(Outcome::Win);
                distances[*node as usize] = Some(distance);
                best_moves[*node as usize] = Some(move_code);
            } else if !unresolved && losing_candidates == moves.len() {
                if let Some((distance, move_code)) = best_loss {
                    outcomes[*node as usize] = Some(Outcome::Loss);
                    distances[*node as usize] = Some(distance);
                    best_moves[*node as usize] = Some(move_code);
                }
            }
        }
        let processed = processed_index + 1;
        if processed == expanded_count || processed % solve_step == 0 {
            eprintln!("[solve_slice_dag] dag_solve_progress processed_nodes={processed}/{expanded_count}");
        }
    }

    eprintln!("[solve_slice_dag] assembling_solution_records");
    let graph_json = if graph_summary.exists() {
        serde_json::from_str::<serde_json::Value>(
            &fs::read_to_string(&graph_summary).map_err(|err| format!("failed reading graph summary: {err}"))?,
        )
        .map_err(|err| format!("failed parsing graph summary: {err}"))?
    } else {
        json!({})
    };
    let root_local_id = graph_json.get("root_local_id").and_then(|value| value.as_u64()).map(|value| value as usize);
    let root_state_key_hex = graph_json.get("root_state_key_hex").and_then(|value| value.as_str()).map(str::to_string);

    let mut solution_records = Vec::with_capacity(state_count);
    let mut resolved_count = 0usize;
    let mut resolved_win_count = 0usize;
    let mut resolved_loss_count = 0usize;
    let mut unknown_state_count = 0usize;
    let mut unresolved_component_count = 0usize;
    let mut frontier_dependent_component_count = 0usize;
    let mut closed_unresolved_component_count = 0usize;

    for local_id in 0..state_count {
        let state = states[local_id];
        let record = if let Some(outcome) = state.terminal_outcome {
            resolved_count += 1;
            match outcome {
                Outcome::Win => resolved_win_count += 1,
                Outcome::Loss => resolved_loss_count += 1,
            }
            SolutionRecord {
                outcome: Some(outcome),
                best_move_code: None,
                distance: state.terminal_distance,
                partial: false,
                terminal_seed: true,
                frontier_dependent: false,
            }
        } else {
            let dense = dense_index_by_local[local_id];
            if dense == u32::MAX {
                unknown_state_count += 1;
                SolutionRecord {
                    outcome: None,
                    best_move_code: None,
                    distance: None,
                    partial: true,
                    terminal_seed: false,
                    frontier_dependent: true,
                }
            } else {
                let moves = &moves_by_node[dense as usize];
                let frontier_edges = moves.iter().filter(|mv| matches!(mv.kind, MoveKind::Unknown)).count();
                let outcome = outcomes[dense as usize];
                if let Some(found) = outcome {
                    resolved_count += 1;
                    match found {
                        Outcome::Win => resolved_win_count += 1,
                        Outcome::Loss => resolved_loss_count += 1,
                    }
                } else {
                    unknown_state_count += 1;
                    unresolved_component_count += 1;
                    if frontier_edges > 0 {
                        frontier_dependent_component_count += 1;
                    } else {
                        closed_unresolved_component_count += 1;
                    }
                }
                SolutionRecord {
                    outcome,
                    best_move_code: best_moves[dense as usize],
                    distance: distances[dense as usize],
                    partial: outcome.is_none(),
                    terminal_seed: false,
                    frontier_dependent: outcome.is_none() && frontier_edges > 0,
                }
            }
        };
        solution_records.push(record);
    }

    write_solution_shard(&solution_output, &solution_records, depth, resolved_count, &rulespec_version)?;

    let frontier_state_count = states.iter().filter(|state| !state.expanded && state.terminal_outcome.is_none()).count();
    let root_record = root_local_id.and_then(|local_id| solution_records.get(local_id).copied());
    let root_status = match root_record.and_then(|record| record.outcome) {
        Some(Outcome::Win) => "win",
        Some(Outcome::Loss) => "loss",
        None => "unknown",
    };

    let top_components_by_size: Vec<_> = (0..usize::min(10, expanded_count))
        .map(|component_id| {
            json!({
                "component_id": component_id,
                "size": 1,
                "internal_edge_count": 0,
                "outgoing_component_count": graph_edges[component_id].len(),
                "frontier_edge_count": moves_by_node[component_id].iter().filter(|mv| matches!(mv.kind, MoveKind::Unknown)).count(),
                "terminal_win_edge_count": moves_by_node[component_id].iter().filter(|mv| matches!(mv.kind, MoveKind::Win)).count(),
                "terminal_loss_edge_count": moves_by_node[component_id].iter().filter(|mv| matches!(mv.kind, MoveKind::Loss)).count(),
                "resolved_win_count": usize::from(outcomes[component_id] == Some(Outcome::Win)),
                "resolved_loss_count": usize::from(outcomes[component_id] == Some(Outcome::Loss)),
                "unresolved_count": usize::from(outcomes[component_id].is_none()),
            })
        })
        .collect();

    if let Some(parent) = output.parent() {
        fs::create_dir_all(parent).map_err(|err| format!("failed creating solve output directory: {err}"))?;
    }
    fs::write(
        &output,
        serde_json::to_string_pretty(&json!({
            "rulespec_version": rulespec_version,
            "depth": depth,
            "state_count": state_count,
            "expanded_state_count": expanded_count,
            "frontier_state_count": frontier_state_count,
            "edge_count": edge_count,
            "solution_record_bytes": SOLUTION_RECORD_BYTES,
            "resolved_win_count": resolved_win_count,
            "resolved_loss_count": resolved_loss_count,
            "resolved_state_count": resolved_count,
            "unknown_state_count": unknown_state_count,
            "component_count": expanded_count,
            "largest_component_size": 1,
            "unresolved_component_count": unresolved_component_count,
            "frontier_dependent_component_count": frontier_dependent_component_count,
            "closed_unresolved_component_count": closed_unresolved_component_count,
            "root_local_id": root_local_id,
            "root_state_key_hex": root_state_key_hex,
            "root_status": root_status,
            "root_best_move_code": root_record.and_then(|record| record.best_move_code),
            "root_distance": root_record.and_then(|record| record.distance),
            "notes": [
                "expanded nodes solved through native DAG propagation",
                "unexpanded frontier states treated as external unknowns",
                "all expanded SCCs are singleton components in this slice"
            ],
            "top_components_by_size": top_components_by_size,
        }))
        .map_err(|err| format!("failed serializing solve summary: {err}"))?
            + "\n",
    )
    .map_err(|err| format!("failed writing solve summary: {err}"))?;

    if let Some(parent) = scc_summary_output.parent() {
        fs::create_dir_all(parent).map_err(|err| format!("failed creating analysis dir: {err}"))?;
    }
    fs::write(
        &scc_summary_output,
        serde_json::to_string_pretty(&json!({
            "rulespec_version": rulespec_version,
            "depth": depth,
            "component_count": expanded_count,
            "largest_component_size": 1,
            "nontrivial_component_count": 0,
            "components_omitted": true,
            "component_stats_omitted": true,
        }))
        .map_err(|err| format!("failed serializing analysis summary: {err}"))?
            + "\n",
    )
    .map_err(|err| format!("failed writing analysis summary: {err}"))?;

    eprintln!(
        "[solve_slice_dag] done resolved={} expanded_states={} elapsed_seconds={:.2}",
        resolved_count,
        expanded_count,
        started.elapsed().as_secs_f64()
    );
    println!("output={}", output.display());
    println!("solution_output={}", solution_output.display());
    println!("scc_summary={}", scc_summary_output.display());
    Ok(0)
}

fn main() {
    match run() {
        Ok(code) => std::process::exit(code),
        Err(error) => {
            eprintln!("{error}");
            std::process::exit(1);
        }
    }
}
