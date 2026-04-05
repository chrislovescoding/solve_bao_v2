pub const TOTAL_SEEDS: usize = 64;
pub const PIT_COUNT: usize = 32;
pub const BAR_COUNT: usize = PIT_COUNT - 1;
pub const SLOT_COUNT: usize = TOTAL_SEEDS + BAR_COUNT;

fn binom(n: usize, k: usize) -> u128 {
    if k > n {
        return 0;
    }
    let k = k.min(n - k);
    let mut result = 1u128;
    for i in 0..k {
        result = result * (n - i) as u128 / (i + 1) as u128;
    }
    result
}

pub fn pack_canonical_pits(pits: [u8; PIT_COUNT]) -> u128 {
    debug_assert_eq!(pits.iter().map(|value| *value as usize).sum::<usize>(), TOTAL_SEEDS);

    let mut rank = 0u128;
    let mut running = 0usize;
    for (index, count) in pits.iter().take(BAR_COUNT).enumerate() {
        running += *count as usize;
        let bar = running + index;
        rank += binom(bar, index + 1);
    }
    rank
}

pub fn unpack_canonical_pits(rank: u128) -> [u8; PIT_COUNT] {
    let mut bars = [0usize; BAR_COUNT];
    let mut remainder = rank;
    let mut upper = SLOT_COUNT - 1;

    for size in (1..=BAR_COUNT).rev() {
        let mut candidate = upper;
        while binom(candidate, size) > remainder {
            candidate -= 1;
        }
        bars[size - 1] = candidate;
        remainder -= binom(candidate, size);
        upper = candidate.saturating_sub(1);
    }

    let mut pits = [0u8; PIT_COUNT];
    let mut previous = usize::MAX;
    for (index, bar) in bars.iter().enumerate() {
        let count = if previous == usize::MAX {
            *bar
        } else {
            bar - previous - 1
        };
        pits[index] = count as u8;
        previous = *bar;
    }
    pits[PIT_COUNT - 1] = (SLOT_COUNT - 1 - previous) as u8;
    pits
}

#[cfg(test)]
mod tests {
    use super::{pack_canonical_pits, unpack_canonical_pits};

    #[test]
    fn roundtrip_initial_position() {
        let pits = [2u8; 32];
        let rank = pack_canonical_pits(pits);
        assert_eq!(unpack_canonical_pits(rank), pits);
    }

    #[test]
    fn roundtrip_extreme_position() {
        let mut pits = [0u8; 32];
        pits[0] = 64;
        let rank = pack_canonical_pits(pits);
        assert_eq!(unpack_canonical_pits(rank), pits);
    }
}

