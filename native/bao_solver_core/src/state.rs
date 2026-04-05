use crate::pack::{pack_canonical_pits, unpack_canonical_pits, PIT_COUNT, TOTAL_SEEDS};
use crate::types::Player;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct StateKey(pub u128);

impl StateKey {
    pub const BYTES: usize = 16;

    pub fn to_be_bytes(self) -> [u8; Self::BYTES] {
        self.0.to_be_bytes()
    }

    pub fn from_be_bytes(bytes: [u8; Self::BYTES]) -> Self {
        Self(u128::from_be_bytes(bytes))
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct StateWork {
    pub pits: [u8; PIT_COUNT],
    pub to_move: Player,
}

impl StateWork {
    pub fn new(pits: [u8; PIT_COUNT], to_move: Player) -> Option<Self> {
        if pits.iter().map(|value| *value as usize).sum::<usize>() != TOTAL_SEEDS {
            return None;
        }
        Some(Self { pits, to_move })
    }

    pub fn canonicalized(self) -> Self {
        let normalized = if self.to_move == Player::North {
            Self {
                pits: rotate_180_and_swap_players(self.pits),
                to_move: Player::South,
            }
        } else {
            self
        };

        let reflected = reflect_columns(normalized.pits);
        if reflected < normalized.pits {
            Self {
                pits: reflected,
                to_move: Player::South,
            }
        } else {
            Self {
                pits: normalized.pits,
                to_move: Player::South,
            }
        }
    }

    pub fn pack_key(self) -> StateKey {
        StateKey(pack_canonical_pits(self.canonicalized().pits))
    }

    pub fn from_key(key: StateKey) -> Self {
        Self {
            pits: unpack_canonical_pits(key.0),
            to_move: Player::South,
        }
    }
}

fn rotate_180_and_swap_players(pits: [u8; PIT_COUNT]) -> [u8; PIT_COUNT] {
    let mut out = [0u8; PIT_COUNT];
    for index in 0..8 {
        out[index] = pits[23 - index];
        out[8 + index] = pits[31 - index];
        out[16 + index] = pits[7 - index];
        out[24 + index] = pits[15 - index];
    }
    out
}

fn reflect_columns(pits: [u8; PIT_COUNT]) -> [u8; PIT_COUNT] {
    let mut out = [0u8; PIT_COUNT];
    for row in 0..4 {
        for column in 0..8 {
            out[row * 8 + column] = pits[row * 8 + (7 - column)];
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::{Player, StateWork};

    #[test]
    fn canonicalization_normalizes_north_to_south() {
        let south = StateWork::new([2u8; 32], Player::South).unwrap();
        let north = StateWork::new([2u8; 32], Player::North).unwrap();
        assert_eq!(south.pack_key(), north.pack_key());
    }
}

