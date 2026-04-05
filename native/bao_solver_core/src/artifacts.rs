use crate::state::StateKey;
use crate::types::{MoveCode, MoveTermination, Outcome, Player};

#[cfg(feature = "serde")]
use serde::{Deserialize, Serialize};

#[cfg_attr(feature = "serde", derive(Serialize, Deserialize))]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct RuleSpecId {
    pub name: &'static str,
    pub version: &'static str,
    pub path: &'static str,
}

pub const RULESPEC_V1_DRAFT: RuleSpecId = RuleSpecId {
    name: "Bao la Kujifunza RuleSpec",
    version: "rulespec-v1.0.0-draft",
    path: "docs/rulespec_v1.md",
};

#[cfg_attr(feature = "serde", derive(Serialize, Deserialize))]
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TraceSowingArtifact {
    pub sequence_index: u32,
    pub start: u8,
    pub seeds: u16,
    pub direction_clockwise: bool,
    pub landing_pit: u8,
    pub capture_triggered: bool,
    pub captured_pit: Option<u8>,
    pub captured_count: u16,
    pub path: Vec<u8>,
}

#[cfg_attr(feature = "serde", derive(Serialize, Deserialize))]
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TraceArtifact {
    pub rulespec_version: &'static str,
    pub source_key: StateKey,
    pub move_code: MoveCode,
    pub terminal_winner: Option<Player>,
    pub termination: Option<MoveTermination>,
    pub outcome_hint: Option<Outcome>,
    pub result_key: Option<StateKey>,
    pub sowings: u32,
    pub seeds_sown: u32,
    pub infinite_move: bool,
    pub trace: Vec<TraceSowingArtifact>,
}

#[cfg_attr(feature = "serde", derive(Serialize, Deserialize))]
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ShardManifest {
    pub artifact_type: String,
    pub rulespec_version: String,
    pub code_revision: String,
    pub item_count: u64,
    pub payload_bytes: u64,
    pub sha256: String,
    pub notes: Vec<String>,
}

