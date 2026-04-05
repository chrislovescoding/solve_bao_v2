use std::collections::{BTreeMap, BTreeSet};

use bao_solver_core::{apply_move, initial_state, legal_moves, RULESPEC_V1_DRAFT, StateKey, StateWork};
use serde::Serialize;

#[derive(Debug, Serialize)]
struct FrontierRecord {
    rulespec_version: &'static str,
    depth: usize,
    canonical_state_key_hex: String,
    state: [u8; 32],
    to_move: &'static str,
    outdegree: usize,
    nonterminal_successor_count: usize,
    terminal_move_count: usize,
    successor_state_key_hexes: Vec<String>,
}

#[derive(Debug, Clone)]
struct FrontierNode {
    state: StateWork,
    depth: usize,
    successor_keys: BTreeSet<StateKey>,
    outdegree: usize,
    terminal_move_count: usize,
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
    nodes.insert(
        initial_key,
        FrontierNode {
            state: initial,
            depth: 0,
            successor_keys: BTreeSet::new(),
            outdegree: 0,
            terminal_move_count: 0,
        },
    );

    for current_depth in 0..depth {
        let mut next_frontier = BTreeMap::new();

        for state in &frontier {
            let key = state.pack_key();
            let moves = legal_moves(*state);
            let mut successor_keys = BTreeSet::new();
            let mut terminal_move_count = 0usize;

            for mv in moves.iter().copied() {
                let result = apply_move(*state, mv, false)?;
                if result.terminal_winner.is_some() {
                    terminal_move_count += 1;
                    continue;
                }

                if let Some(next_state) = result.state {
                    let canonical = next_state.canonicalized();
                    let next_key = canonical.pack_key();
                    successor_keys.insert(next_key);
                    if !nodes.contains_key(&next_key) && !next_frontier.contains_key(&next_key) {
                        next_frontier.insert(next_key, canonical);
                    }
                }
            }

            let entry = nodes
                .get_mut(&key)
                .ok_or_else(|| "internal frontier node missing".to_string())?;
            entry.outdegree = moves.len();
            entry.terminal_move_count = terminal_move_count;
            entry.successor_keys = successor_keys;
        }

        frontier = next_frontier.values().copied().collect();
        for (key, state) in next_frontier {
            nodes.entry(key).or_insert(FrontierNode {
                state,
                depth: current_depth + 1,
                successor_keys: BTreeSet::new(),
                outdegree: 0,
                terminal_move_count: 0,
            });
        }
    }

    for (key, node) in nodes {
        let record = FrontierRecord {
            rulespec_version: RULESPEC_V1_DRAFT.version,
            depth: node.depth,
            canonical_state_key_hex: format!("{:032x}", key.0),
            state: node.state.pits,
            to_move: "south",
            outdegree: node.outdegree,
            nonterminal_successor_count: node.successor_keys.len(),
            terminal_move_count: node.terminal_move_count,
            successor_state_key_hexes: node
                .successor_keys
                .iter()
                .map(|successor| format!("{:032x}", successor.0))
                .collect(),
        };

        let payload = serde_json::to_string(&record)
            .map_err(|err| format!("failed to serialize frontier record: {err}"))?;
        println!("{payload}");
    }

    Ok(())
}
