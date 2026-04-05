use std::collections::{HashMap, HashSet};
use std::fs::File;
use std::io::{BufWriter, Write};
use std::path::PathBuf;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::Instant;

use bao_solver_core::{
    apply_move, has_legal_move, initial_state, legal_moves, MoveCode, MoveKind, MoveTermination,
    Player, StateKey, StateWork, RULESPEC_V1_DRAFT,
};
use rayon::prelude::*;
use serde::Serialize;

const HEADER_BYTES: u16 = 64;
const FORMAT_VERSION: u16 = 1;
const STATE_RECORD_BYTES: u16 = 32;
const EDGE_RECORD_BYTES: u16 = 18;
const ADJ_EDGE_RECORD_BYTES: u16 = 12;
const OFFSET_RECORD_BYTES: u16 = 4;
const RULESPEC_FIELD_BYTES: usize = 24;
const TERMINAL_RESULT_ID: u32 = u32::MAX;
const STATE_MAGIC: [u8; 8] = *b"BAOSTATE";
const EDGE_MAGIC: [u8; 8] = *b"BAOEDGE!";
const ADJ_MAGIC: [u8; 8] = *b"BAOADJ!!";

#[derive(Debug, Clone)]
struct NodeRecord {
    state: StateWork,
    depth: usize,
    expanded: bool,
    outdegree: usize,
    nonterminal_successor_count: usize,
    terminal_move_count: usize,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct EdgeRecord {
    source_key: StateKey,
    source_depth: usize,
    move_code: MoveCode,
    move_kind: MoveKind,
    sowings: u32,
    seeds_sown: u32,
    captures: u32,
    infinite_move: bool,
    termination: Option<MoveTermination>,
    terminal_winner: Option<Player>,
    result_key: Option<StateKey>,
}

#[derive(Debug)]
struct LayerExpansion {
    source_key: StateKey,
    outdegree: usize,
    nonterminal_successor_count: usize,
    terminal_move_count: usize,
    edges: Vec<EdgeRecord>,
    next_states: Vec<(StateKey, StateWork)>,
}

#[derive(Debug, Serialize)]
struct ExportSummary {
    rulespec_version: &'static str,
    sorted_by: &'static str,
    depth: usize,
    header_bytes: u16,
    state_record_bytes: u16,
    edge_record_bytes: u16,
    adjacency_edge_record_bytes: u16,
    adjacency_offset_record_bytes: u16,
    root_state_key_hex: String,
    root_local_id: u32,
    state_count: usize,
    expanded_state_count: usize,
    terminal_state_count: usize,
    edge_count: usize,
    terminal_edge_count: usize,
    nonterminal_edge_count: usize,
    states_output: String,
    edges_output: String,
    adjacency_output: String,
    traversal_ns: u64,
    sort_ns: u64,
    local_id_ns: u64,
    state_annotation_ns: u64,
    state_write_ns: u64,
    edge_write_ns: u64,
    adjacency_write_ns: u64,
    total_ns: u64,
}

fn player_code(player: Option<Player>) -> u8 {
    match player {
        None => 0,
        Some(Player::South) => 1,
        Some(Player::North) => 2,
    }
}

fn termination_code(termination: Option<MoveTermination>) -> u8 {
    match termination {
        None => 0,
        Some(MoveTermination::LandedInEmpty) => 1,
        Some(MoveTermination::CurrentPlayerFrontRowEmpty) => 2,
        Some(MoveTermination::OpponentFrontRowEmpty) => 3,
        Some(MoveTermination::InfiniteMove) => 4,
    }
}

fn state_flags(node: &NodeRecord, terminal_winner: Option<Player>) -> u8 {
    let mut flags = 0u8;
    if node.expanded {
        flags |= 1 << 0;
    }
    flags | (player_code(terminal_winner) << 1)
}

fn state_terminal_outcome_code(node: &NodeRecord, terminal_winner: Option<Player>) -> u8 {
    match terminal_winner {
        None => 0,
        Some(winner) if winner == node.state.to_move => 1,
        Some(_) => 2,
    }
}

fn state_terminal_distance(terminal_winner: Option<Player>) -> u8 {
    if terminal_winner.is_some() {
        0
    } else {
        u8::MAX
    }
}

fn edge_flags(edge: &EdgeRecord) -> u8 {
    let mut flags = 0u8;
    if edge.move_kind == MoveKind::Mtaji {
        flags |= 1 << 0;
    }
    if edge.infinite_move {
        flags |= 1 << 1;
    }
    flags |= termination_code(edge.termination) << 2;
    flags |= player_code(edge.terminal_winner) << 5;
    flags
}

fn write_header(
    writer: &mut BufWriter<File>,
    magic: [u8; 8],
    record_bytes: u16,
    depth: usize,
    record_count: u64,
    payload_bytes: u64,
    aux_count: u64,
) -> Result<(), String> {
    let mut header = [0u8; HEADER_BYTES as usize];
    let mut offset = 0usize;

    header[offset..offset + 8].copy_from_slice(&magic);
    offset += 8;
    header[offset..offset + 2].copy_from_slice(&FORMAT_VERSION.to_le_bytes());
    offset += 2;
    header[offset..offset + 2].copy_from_slice(&HEADER_BYTES.to_le_bytes());
    offset += 2;
    header[offset..offset + 2].copy_from_slice(&record_bytes.to_le_bytes());
    offset += 2;
    header[offset..offset + 2].copy_from_slice(&(depth as u16).to_le_bytes());
    offset += 2;
    header[offset..offset + 8].copy_from_slice(&record_count.to_le_bytes());
    offset += 8;
    header[offset..offset + 8].copy_from_slice(&payload_bytes.to_le_bytes());
    offset += 8;
    header[offset..offset + 8].copy_from_slice(&aux_count.to_le_bytes());
    offset += 8;

    let version_bytes = RULESPEC_V1_DRAFT.version.as_bytes();
    if version_bytes.len() > RULESPEC_FIELD_BYTES {
        return Err("rulespec version does not fit in header field".to_string());
    }
    header[offset..offset + version_bytes.len()].copy_from_slice(version_bytes);

    writer
        .write_all(&header)
        .map_err(|err| format!("failed writing shard header: {err}"))?;
    Ok(())
}

fn write_state_record(
    writer: &mut BufWriter<File>,
    key: StateKey,
    node: &NodeRecord,
    terminal_winner: Option<Player>,
) -> Result<(), String> {
    let mut record = [0u8; STATE_RECORD_BYTES as usize];
    let mut offset = 0usize;

    record[offset..offset + 16].copy_from_slice(&key.to_be_bytes());
    offset += 16;
    record[offset] = node.depth as u8;
    offset += 1;
    record[offset] = state_flags(node, terminal_winner);
    offset += 1;
    record[offset] = state_terminal_outcome_code(node, terminal_winner);
    offset += 1;
    record[offset] = state_terminal_distance(terminal_winner);
    offset += 1;
    record[offset..offset + 4].copy_from_slice(&(node.outdegree as u32).to_le_bytes());
    offset += 4;
    record[offset..offset + 4]
        .copy_from_slice(&(node.nonterminal_successor_count as u32).to_le_bytes());
    offset += 4;
    record[offset..offset + 4].copy_from_slice(&(node.terminal_move_count as u32).to_le_bytes());

    writer
        .write_all(&record)
        .map_err(|err| format!("failed writing state record: {err}"))?;
    Ok(())
}

fn write_edge_record(
    writer: &mut BufWriter<File>,
    edge: &EdgeRecord,
    local_id_by_key: &HashMap<StateKey, u32>,
) -> Result<(), String> {
    let mut record = [0u8; EDGE_RECORD_BYTES as usize];
    let mut offset = 0usize;

    let source_id = *local_id_by_key
        .get(&edge.source_key)
        .ok_or_else(|| "missing source local id for edge record".to_string())?;
    let result_id = match edge.result_key {
        Some(key) => *local_id_by_key
            .get(&key)
            .ok_or_else(|| "missing result local id for edge record".to_string())?,
        None => TERMINAL_RESULT_ID,
    };

    record[offset..offset + 4].copy_from_slice(&source_id.to_le_bytes());
    offset += 4;
    record[offset..offset + 4].copy_from_slice(&result_id.to_le_bytes());
    offset += 4;
    record[offset..offset + 2].copy_from_slice(&(edge.sowings as u16).to_le_bytes());
    offset += 2;
    record[offset..offset + 2].copy_from_slice(&(edge.seeds_sown as u16).to_le_bytes());
    offset += 2;
    record[offset..offset + 2].copy_from_slice(&(edge.captures as u16).to_le_bytes());
    offset += 2;
    record[offset] = edge.move_code.raw();
    offset += 1;
    record[offset] = edge.source_depth as u8;
    offset += 1;
    record[offset] = edge_flags(edge);
    offset += 1;
    record[offset] = 0;

    writer
        .write_all(&record)
        .map_err(|err| format!("failed writing edge record: {err}"))?;
    Ok(())
}

fn write_adjacency_edge_record(
    writer: &mut BufWriter<File>,
    edge: &EdgeRecord,
    local_id_by_key: &HashMap<StateKey, u32>,
) -> Result<(), String> {
    let mut record = [0u8; ADJ_EDGE_RECORD_BYTES as usize];
    let mut offset = 0usize;

    let result_id = match edge.result_key {
        Some(key) => *local_id_by_key
            .get(&key)
            .ok_or_else(|| "missing result local id for adjacency edge record".to_string())?,
        None => TERMINAL_RESULT_ID,
    };

    let captures = u8::try_from(edge.captures)
        .map_err(|_| format!("captures count {} does not fit in adjacency record", edge.captures))?;

    record[offset..offset + 4].copy_from_slice(&result_id.to_le_bytes());
    offset += 4;
    record[offset..offset + 2].copy_from_slice(&(edge.sowings as u16).to_le_bytes());
    offset += 2;
    record[offset..offset + 2].copy_from_slice(&(edge.seeds_sown as u16).to_le_bytes());
    offset += 2;
    record[offset] = captures;
    offset += 1;
    record[offset] = edge.move_code.raw();
    offset += 1;
    record[offset] = edge_flags(edge);
    offset += 1;
    record[offset] = 0;

    writer
        .write_all(&record)
        .map_err(|err| format!("failed writing adjacency edge record: {err}"))?;
    Ok(())
}

fn expand_state(
    state: StateWork,
    source_depth: usize,
) -> Result<LayerExpansion, String> {
    let source_key = state.pack_key();
    let moves = legal_moves(state);
    let mut successor_keys = HashSet::new();
    let mut terminal_move_count = 0usize;
    let mut edges = Vec::with_capacity(moves.len());
    let mut next_states = Vec::with_capacity(moves.len());

    for mv in moves.iter().copied() {
        let result = apply_move(state, mv, false)?;
        let canonical_state = result.state.map(|next_state| {
            let canonical = next_state.canonicalized();
            (canonical.pack_key(), canonical)
        });
        let result_key = canonical_state.map(|(key, _)| key);

        if result.terminal_winner.is_some() {
            terminal_move_count += 1;
        } else if let Some(next_key) = result_key {
            successor_keys.insert(next_key);
        }

        edges.push(EdgeRecord {
            source_key,
            source_depth,
            move_code: mv,
            move_kind: result.move_kind,
            sowings: result.sowings,
            seeds_sown: result.seeds_sown,
            captures: result.captures,
            infinite_move: result.infinite_move,
            termination: result.termination,
            terminal_winner: result.terminal_winner,
            result_key,
        });

        if let Some((next_key, next_state)) = canonical_state {
            next_states.push((next_key, next_state));
        }
    }

    Ok(LayerExpansion {
        source_key,
        outdegree: moves.len(),
        nonterminal_successor_count: successor_keys.len(),
        terminal_move_count,
        edges,
        next_states,
    })
}

fn main() -> Result<(), String> {
    let mut args = std::env::args().skip(1);
    let mut depth = 6usize;
    let mut states_output = PathBuf::from("artifacts/shards/native_state_slice_depth6.bin");
    let mut edges_output = PathBuf::from("artifacts/shards/native_edge_slice_depth6.bin");
    let mut adjacency_output = PathBuf::from("artifacts/shards/native_adjacency_slice_depth6.bin");
    let total_started = Instant::now();

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
            "--states-output" => {
                let value = args
                    .next()
                    .ok_or_else(|| "expected path after --states-output".to_string())?;
                states_output = PathBuf::from(value);
            }
            "--edges-output" => {
                let value = args
                    .next()
                    .ok_or_else(|| "expected path after --edges-output".to_string())?;
                edges_output = PathBuf::from(value);
            }
            "--adjacency-output" => {
                let value = args
                    .next()
                    .ok_or_else(|| "expected path after --adjacency-output".to_string())?;
                adjacency_output = PathBuf::from(value);
            }
            other => return Err(format!("unknown argument: {other}")),
        }
    }

    if let Some(parent) = states_output.parent() {
        std::fs::create_dir_all(parent)
            .map_err(|err| format!("failed creating state output directory: {err}"))?;
    }
    if let Some(parent) = edges_output.parent() {
        std::fs::create_dir_all(parent)
            .map_err(|err| format!("failed creating edge output directory: {err}"))?;
    }
    if let Some(parent) = adjacency_output.parent() {
        std::fs::create_dir_all(parent)
            .map_err(|err| format!("failed creating adjacency output directory: {err}"))?;
    }

    eprintln!(
        "[export_binary_graph_slice] start depth={} states_output={} edges_output={} adjacency_output={}",
        depth,
        states_output.display(),
        edges_output.display(),
        adjacency_output.display()
    );
    let traversal_started = Instant::now();
    let initial = initial_state().canonicalized();
    let initial_key = initial.pack_key();
    let mut frontier = vec![initial];
    let mut nodes = HashMap::new();
    let mut edges = Vec::new();

    nodes.insert(
        initial_key,
        NodeRecord {
            state: initial,
            depth: 0,
            expanded: false,
            outdegree: 0,
            nonterminal_successor_count: 0,
            terminal_move_count: 0,
        },
    );

    for current_depth in 0..depth {
        eprintln!(
            "[export_binary_graph_slice] expand depth_layer={} frontier_states={} nodes_so_far={} edges_so_far={} elapsed_seconds={:.2}",
            current_depth,
            frontier.len(),
            nodes.len(),
            edges.len(),
            total_started.elapsed().as_secs_f64()
        );
        let mut next_frontier = HashMap::new();
        let frontier_len = frontier.len();
        let progress_step = usize::max(1, frontier_len / 20);
        let progress_counter = AtomicUsize::new(0);
        let layer_results = frontier
            .par_iter()
            .copied()
            .map(|state| {
                let expansion = expand_state(state, current_depth);
                let completed = progress_counter.fetch_add(1, Ordering::Relaxed) + 1;
                if completed == frontier_len || completed % progress_step == 0 {
                    eprintln!(
                        "[export_binary_graph_slice] layer_progress depth_layer={} processed={}/{} elapsed_seconds={:.2}",
                        current_depth,
                        completed,
                        frontier_len,
                        total_started.elapsed().as_secs_f64()
                    );
                }
                expansion
            })
            .collect::<Vec<_>>();

        for expansion in layer_results {
            let expansion = expansion?;
            let entry = nodes
                .get_mut(&expansion.source_key)
                .ok_or_else(|| "internal binary graph-slice node missing".to_string())?;
            entry.expanded = true;
            entry.outdegree = expansion.outdegree;
            entry.nonterminal_successor_count = expansion.nonterminal_successor_count;
            entry.terminal_move_count = expansion.terminal_move_count;

            edges.extend(expansion.edges);
            for (next_key, next_state) in expansion.next_states {
                if !nodes.contains_key(&next_key) {
                    next_frontier.entry(next_key).or_insert(next_state);
                }
            }
        }

        frontier = next_frontier.values().copied().collect();
        for (key, state) in next_frontier {
            nodes.entry(key).or_insert(NodeRecord {
                state,
                depth: current_depth + 1,
                expanded: false,
                outdegree: 0,
                nonterminal_successor_count: 0,
                terminal_move_count: 0,
            });
        }
        eprintln!(
            "[export_binary_graph_slice] expanded depth_layer={} next_frontier_states={} total_nodes={} total_edges={} elapsed_seconds={:.2}",
            current_depth,
            frontier.len(),
            nodes.len(),
            edges.len(),
            total_started.elapsed().as_secs_f64()
        );
    }
    let traversal_ns = traversal_started.elapsed().as_nanos() as u64;

    eprintln!(
        "[export_binary_graph_slice] traversal_complete states={} edges={} elapsed_seconds={:.2}",
        nodes.len(),
        edges.len(),
        total_started.elapsed().as_secs_f64()
    );
    let sort_started = Instant::now();
    edges.par_sort_unstable_by_key(|edge| {
        (
            edge.source_key,
            edge.source_depth,
            edge.move_code.raw(),
            edge.result_key.unwrap_or(StateKey(0)),
        )
    });
    let mut sorted_node_keys = nodes.keys().copied().collect::<Vec<_>>();
    sorted_node_keys.par_sort_unstable();
    let sort_ns = sort_started.elapsed().as_nanos() as u64;
    eprintln!(
        "[export_binary_graph_slice] sort_complete state_count={} edge_count={} elapsed_seconds={:.2}",
        sorted_node_keys.len(),
        edges.len(),
        total_started.elapsed().as_secs_f64()
    );

    let local_id_started = Instant::now();
    let local_id_by_key: HashMap<_, _> = sorted_node_keys
        .iter()
        .enumerate()
        .map(|(index, key)| (*key, index as u32))
        .collect();
    let root_local_id = *local_id_by_key
        .get(&initial_key)
        .ok_or_else(|| "initial state key missing from local-id map".to_string())?;
    let local_id_ns = local_id_started.elapsed().as_nanos() as u64;
    eprintln!(
        "[export_binary_graph_slice] local_id_complete root_local_id={} elapsed_seconds={:.2}",
        root_local_id,
        total_started.elapsed().as_secs_f64()
    );

    let annotation_started = Instant::now();
    let terminal_winner_by_key: HashMap<_, _> = sorted_node_keys
        .par_iter()
        .map(|key| {
            let node = nodes
                .get(key)
                .expect("sorted node key must exist in node map during annotation");
            let terminal = if node.expanded {
                if node.outdegree == 0 {
                    Some(node.state.to_move.opponent())
                } else {
                    None
                }
            } else if has_legal_move(node.state) {
                None
            } else {
                Some(node.state.to_move.opponent())
            };
            (*key, terminal)
        })
        .collect();
    let expanded_state_count = nodes.values().filter(|node| node.expanded).count();
    let terminal_state_count = terminal_winner_by_key
        .values()
        .filter(|winner| winner.is_some())
        .count();
    let terminal_edge_count = edges.iter().filter(|edge| edge.terminal_winner.is_some()).count();
    let nonterminal_edge_count = edges.len() - terminal_edge_count;
    let state_annotation_ns = annotation_started.elapsed().as_nanos() as u64;
    eprintln!(
        "[export_binary_graph_slice] annotation_complete expanded_states={} terminal_states={} terminal_edges={} elapsed_seconds={:.2}",
        expanded_state_count,
        terminal_state_count,
        terminal_edge_count,
        total_started.elapsed().as_secs_f64()
    );

    let state_payload_bytes = sorted_node_keys.len() as u64 * u64::from(STATE_RECORD_BYTES);
    let edge_payload_bytes = edges.len() as u64 * u64::from(EDGE_RECORD_BYTES);
    let adjacency_offset_count = sorted_node_keys.len() + 1;
    let adjacency_payload_bytes =
        adjacency_offset_count as u64 * u64::from(OFFSET_RECORD_BYTES)
            + edges.len() as u64 * u64::from(ADJ_EDGE_RECORD_BYTES);

    let state_write_started = Instant::now();
    let mut state_writer = BufWriter::new(
        File::create(&states_output).map_err(|err| format!("failed creating state shard: {err}"))?,
    );
    write_header(
        &mut state_writer,
        STATE_MAGIC,
        STATE_RECORD_BYTES,
        depth,
        sorted_node_keys.len() as u64,
        state_payload_bytes,
        expanded_state_count as u64,
    )?;
    for key in &sorted_node_keys {
        let node = nodes
            .get(key)
            .expect("sorted node key must exist in node map during state write");
        let terminal_winner = *terminal_winner_by_key
            .get(key)
            .ok_or_else(|| "missing cached terminal winner for state record".to_string())?;
        write_state_record(&mut state_writer, *key, node, terminal_winner)?;
    }
    state_writer
        .flush()
        .map_err(|err| format!("failed flushing state shard: {err}"))?;
    let state_write_ns = state_write_started.elapsed().as_nanos() as u64;
    eprintln!(
        "[export_binary_graph_slice] state_write_complete payload_bytes={} elapsed_seconds={:.2}",
        state_payload_bytes,
        total_started.elapsed().as_secs_f64()
    );

    let edge_write_started = Instant::now();
    let mut edge_writer = BufWriter::new(
        File::create(&edges_output).map_err(|err| format!("failed creating edge shard: {err}"))?,
    );
    write_header(
        &mut edge_writer,
        EDGE_MAGIC,
        EDGE_RECORD_BYTES,
        depth,
        edges.len() as u64,
        edge_payload_bytes,
        terminal_edge_count as u64,
    )?;
    for edge in &edges {
        write_edge_record(&mut edge_writer, edge, &local_id_by_key)?;
    }
    edge_writer
        .flush()
        .map_err(|err| format!("failed flushing edge shard: {err}"))?;
    let edge_write_ns = edge_write_started.elapsed().as_nanos() as u64;
    eprintln!(
        "[export_binary_graph_slice] edge_write_complete payload_bytes={} elapsed_seconds={:.2}",
        edge_payload_bytes,
        total_started.elapsed().as_secs_f64()
    );

    let adjacency_write_started = Instant::now();
    let mut adjacency_offsets = vec![0u32; adjacency_offset_count];
    for edge in &edges {
        let source_id = *local_id_by_key
            .get(&edge.source_key)
            .ok_or_else(|| "missing source local id while building adjacency offsets".to_string())?
            as usize;
        adjacency_offsets[source_id + 1] += 1;
    }
    for index in 1..adjacency_offsets.len() {
        let previous = adjacency_offsets[index - 1];
        adjacency_offsets[index] += previous;
    }

    let mut adjacency_writer = BufWriter::new(
        File::create(&adjacency_output)
            .map_err(|err| format!("failed creating adjacency shard: {err}"))?,
    );
    write_header(
        &mut adjacency_writer,
        ADJ_MAGIC,
        ADJ_EDGE_RECORD_BYTES,
        depth,
        edges.len() as u64,
        adjacency_payload_bytes,
        sorted_node_keys.len() as u64,
    )?;
    for offset in &adjacency_offsets {
        adjacency_writer
            .write_all(&offset.to_le_bytes())
            .map_err(|err| format!("failed writing adjacency offset table: {err}"))?;
    }
    for edge in &edges {
        write_adjacency_edge_record(&mut adjacency_writer, edge, &local_id_by_key)?;
    }
    adjacency_writer
        .flush()
        .map_err(|err| format!("failed flushing adjacency shard: {err}"))?;
    let adjacency_write_ns = adjacency_write_started.elapsed().as_nanos() as u64;
    let total_ns = total_started.elapsed().as_nanos() as u64;
    eprintln!(
        "[export_binary_graph_slice] adjacency_write_complete payload_bytes={} elapsed_seconds={:.2}",
        adjacency_payload_bytes,
        total_started.elapsed().as_secs_f64()
    );

    let summary = ExportSummary {
        rulespec_version: RULESPEC_V1_DRAFT.version,
        sorted_by: "canonical_state_key",
        depth,
        header_bytes: HEADER_BYTES,
        state_record_bytes: STATE_RECORD_BYTES,
        edge_record_bytes: EDGE_RECORD_BYTES,
        adjacency_edge_record_bytes: ADJ_EDGE_RECORD_BYTES,
        adjacency_offset_record_bytes: OFFSET_RECORD_BYTES,
        root_state_key_hex: format!("{:032x}", initial_key.0),
        root_local_id,
        state_count: sorted_node_keys.len(),
        expanded_state_count,
        terminal_state_count,
        edge_count: edges.len(),
        terminal_edge_count,
        nonterminal_edge_count,
        states_output: states_output.display().to_string(),
        edges_output: edges_output.display().to_string(),
        adjacency_output: adjacency_output.display().to_string(),
        traversal_ns,
        sort_ns,
        local_id_ns,
        state_annotation_ns,
        state_write_ns,
        edge_write_ns,
        adjacency_write_ns,
        total_ns,
    };

    let payload = serde_json::to_string_pretty(&summary)
        .map_err(|err| format!("failed serializing binary export summary: {err}"))?;
    eprintln!(
        "[export_binary_graph_slice] done total_seconds={:.2}",
        total_started.elapsed().as_secs_f64()
    );
    println!("{payload}");
    Ok(())
}
