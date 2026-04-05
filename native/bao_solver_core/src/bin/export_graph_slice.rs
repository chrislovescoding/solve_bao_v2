use std::collections::{BTreeMap, BTreeSet};

use bao_solver_core::{
    apply_move, initial_state, legal_moves, winner, MoveCode, MoveKind, MoveTermination, Player,
    RULESPEC_V1_DRAFT, StateKey, StateWork,
};
use serde::Serialize;

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

#[derive(Debug, Serialize)]
struct StatePayload {
    record_type: &'static str,
    rulespec_version: &'static str,
    canonical_state_key_hex: String,
    depth: usize,
    state: [u8; 32],
    to_move: &'static str,
    expanded: bool,
    state_terminal_winner: Option<&'static str>,
    state_terminal_outcome: Option<&'static str>,
    state_terminal_distance: Option<u32>,
    outdegree: usize,
    nonterminal_successor_count: usize,
    terminal_move_count: usize,
}

#[derive(Debug, Serialize)]
struct EdgePayload {
    record_type: &'static str,
    rulespec_version: &'static str,
    source_state_key_hex: String,
    source_depth: usize,
    move_code: u8,
    move_kind: &'static str,
    sowings: u32,
    seeds_sown: u32,
    captures: u32,
    infinite_move: bool,
    termination: Option<&'static str>,
    terminal_winner: Option<&'static str>,
    result_state_key_hex: Option<String>,
}

fn player_name(player: Player) -> &'static str {
    match player {
        Player::South => "south",
        Player::North => "north",
    }
}

fn move_kind_name(kind: MoveKind) -> &'static str {
    match kind {
        MoveKind::Mtaji => "mtaji",
        MoveKind::Takasa => "takasa",
    }
}

fn termination_name(termination: MoveTermination) -> &'static str {
    match termination {
        MoveTermination::LandedInEmpty => "landed_in_empty",
        MoveTermination::CurrentPlayerFrontRowEmpty => "current_player_front_row_empty",
        MoveTermination::OpponentFrontRowEmpty => "opponent_front_row_empty",
        MoveTermination::InfiniteMove => "infinite_move",
    }
}

fn terminal_outcome_name(state: StateWork, winner: Option<Player>) -> Option<&'static str> {
    match winner {
        None => None,
        Some(player) if player == state.to_move => Some("win"),
        Some(_) => Some("loss"),
    }
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

    let initial = initial_state().canonicalized();
    let initial_key = initial.pack_key();
    let mut frontier = vec![initial];
    let mut nodes = BTreeMap::new();
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
        let mut next_frontier = BTreeMap::new();

        for state in &frontier {
            let source_key = state.pack_key();
            let moves = legal_moves(*state);
            let mut successor_keys = BTreeSet::new();
            let mut terminal_move_count = 0usize;

            for mv in moves.iter().copied() {
                let result = apply_move(*state, mv, false)?;
                let result_key = result.state.map(|next_state| next_state.canonicalized().pack_key());

                if result.terminal_winner.is_some() {
                    terminal_move_count += 1;
                } else if let Some(next_key) = result_key {
                    successor_keys.insert(next_key);
                }

                edges.push(EdgeRecord {
                    source_key,
                    source_depth: current_depth,
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

                if let Some(next_state) = result.state {
                    let canonical = next_state.canonicalized();
                    let next_key = canonical.pack_key();
                    if !nodes.contains_key(&next_key) && !next_frontier.contains_key(&next_key) {
                        next_frontier.insert(next_key, canonical);
                    }
                }
            }

            let entry = nodes
                .get_mut(&source_key)
                .ok_or_else(|| "internal graph-slice node missing".to_string())?;
            entry.expanded = true;
            entry.outdegree = moves.len();
            entry.nonterminal_successor_count = successor_keys.len();
            entry.terminal_move_count = terminal_move_count;
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
    }

    edges.sort_unstable_by_key(|edge| {
        (
            edge.source_key,
            edge.source_depth,
            edge.move_code.raw(),
            edge.result_key.unwrap_or(StateKey(0)),
        )
    });

    for (key, node) in &nodes {
        let state_terminal_winner = winner(node.state);
        let payload = StatePayload {
            record_type: "state",
            rulespec_version: RULESPEC_V1_DRAFT.version,
            canonical_state_key_hex: format!("{:032x}", key.0),
            depth: node.depth,
            state: node.state.pits,
            to_move: "south",
            expanded: node.expanded,
            state_terminal_winner: state_terminal_winner.map(player_name),
            state_terminal_outcome: terminal_outcome_name(node.state, state_terminal_winner),
            state_terminal_distance: state_terminal_winner.map(|_| 0),
            outdegree: node.outdegree,
            nonterminal_successor_count: node.nonterminal_successor_count,
            terminal_move_count: node.terminal_move_count,
        };
        println!(
            "{}",
            serde_json::to_string(&payload).map_err(|err| format!("failed to serialize state payload: {err}"))?
        );
    }

    for edge in &edges {
        let payload = EdgePayload {
            record_type: "edge",
            rulespec_version: RULESPEC_V1_DRAFT.version,
            source_state_key_hex: format!("{:032x}", edge.source_key.0),
            source_depth: edge.source_depth,
            move_code: edge.move_code.raw(),
            move_kind: move_kind_name(edge.move_kind),
            sowings: edge.sowings,
            seeds_sown: edge.seeds_sown,
            captures: edge.captures,
            infinite_move: edge.infinite_move,
            termination: edge.termination.map(termination_name),
            terminal_winner: edge.terminal_winner.map(player_name),
            result_state_key_hex: edge.result_key.map(|key| format!("{:032x}", key.0)),
        };
        println!(
            "{}",
            serde_json::to_string(&payload).map_err(|err| format!("failed to serialize edge payload: {err}"))?
        );
    }

    Ok(())
}
