//! Weight benchmarks. This is where your paper's validation-latency table comes
//! from — run with `--features runtime-benchmarks` and the FRAME benchmarking CLI,
//! then `benchmark pallet ... --output weights.rs`. Report the machine spec.
#![cfg(feature = "runtime-benchmarks")]
use super::*;
use frame_benchmarking::v2::*;
use frame_system::RawOrigin;

#[benchmarks]
mod benchmarks {
    use super::*;

    #[benchmark]
    fn transfer() {
        let caller: T::AccountId = whitelisted_caller();
        // NOTE: seed a valid rule/attestation/CRR here via your registry pallets'
        // benchmark helpers so the happy path is measured end to end.
        #[extrinsic_call]
        _(RawOrigin::Signed(caller), 1u128, whitelisted_caller(), 36u16, T::Hash::default(), T::Hash::default());
    }

    impl_benchmark_test_suite!(Pallet, crate::mock::new_test_ext(), crate::mock::Test);
}
