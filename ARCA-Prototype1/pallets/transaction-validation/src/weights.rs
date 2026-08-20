//! Placeholder weights. Replace with generated output from the FRAME benchmark CLI.
use frame_support::weights::Weight;

pub trait WeightInfo {
    fn transfer() -> Weight;
}

// Unit impl for tests.
impl WeightInfo for () {
    fn transfer() -> Weight { Weight::from_parts(10_000, 0) }
}
