#[cfg(feature = "serde")]
use serde::{Deserialize, Serialize};

#[cfg_attr(feature = "serde", derive(Serialize, Deserialize))]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Player {
    South = 0,
    North = 1,
}

impl Player {
    pub fn opponent(self) -> Self {
        match self {
            Self::South => Self::North,
            Self::North => Self::South,
        }
    }
}

#[cfg_attr(feature = "serde", derive(Serialize, Deserialize))]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Direction {
    Clockwise = 0,
    Anticlockwise = 1,
}

#[cfg_attr(feature = "serde", derive(Serialize, Deserialize))]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum MoveKind {
    Mtaji,
    Takasa,
}

#[cfg_attr(feature = "serde", derive(Serialize, Deserialize))]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum MoveTermination {
    LandedInEmpty,
    CurrentPlayerFrontRowEmpty,
    OpponentFrontRowEmpty,
    InfiniteMove,
}

#[cfg_attr(feature = "serde", derive(Serialize, Deserialize))]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct MoveCode(u8);

impl MoveCode {
    pub fn new(start: u8, direction: Direction) -> Option<Self> {
        if start >= 32 {
            return None;
        }
        let direction_bit = match direction {
            Direction::Clockwise => 0,
            Direction::Anticlockwise => 1,
        };
        Some(Self((start << 1) | direction_bit))
    }

    pub fn raw(self) -> u8 {
        self.0
    }

    pub fn start(self) -> u8 {
        self.0 >> 1
    }

    pub fn direction(self) -> Direction {
        if (self.0 & 1) == 0 {
            Direction::Clockwise
        } else {
            Direction::Anticlockwise
        }
    }
}

#[cfg_attr(feature = "serde", derive(Serialize, Deserialize))]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Outcome {
    Win,
    Loss,
}

#[cfg_attr(feature = "serde", derive(Serialize, Deserialize))]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct SolveRecord {
    pub outcome: Outcome,
    pub best_move: Option<MoveCode>,
    pub distance: u32,
}

