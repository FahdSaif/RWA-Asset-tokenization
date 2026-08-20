//! Mock runtime for the unit tests.
//!
//! NOTE: the `construct_runtime!` version syntax and the exact set of required
//! `Config` associated types change between polkadot-sdk releases. After
//! bootstrap.sh brings in the template, align the imports/types below with the
//! template's own mock (copy its `mock.rs` header verbatim, then add our pallets).
//! Treat the helper fns at the bottom as the stable part; the wiring is the churny part.

use crate as pallet_transaction_validation;
use frame_support::{derive_impl, parameter_types};
use sp_runtime::BuildStorage;

pub use frame_system::RuntimeOrigin as _; // re-export convenience in some sdk versions

type Block = frame_system::mocking::MockBlock<Test>;

frame_support::construct_runtime!(
    pub enum Test {
        System: frame_system,
        RuleRegistry: pallet_rule_registry,
        Verification: pallet_verification,
        AuditLog: pallet_audit_log,
        TxValidation: pallet_transaction_validation,
    }
);

#[derive_impl(frame_system::config_preludes::TestDefaultConfig)]
impl frame_system::Config for Test {
    type Block = Block;
    type AccountId = u64;
}

impl pallet_rule_registry::Config for Test {
    type RuntimeEvent = RuntimeEvent;
}
impl pallet_verification::Config for Test {
    type RuntimeEvent = RuntimeEvent;
}
impl pallet_audit_log::Config for Test {
    type RuntimeEvent = RuntimeEvent;
}
impl pallet_transaction_validation::Config for Test {
    type RuntimeEvent = RuntimeEvent;
    type WeightInfo = ();
}

pub fn new_test_ext() -> sp_io::TestExternalities {
    frame_system::GenesisConfig::<Test>::default().build_storage().unwrap().into()
}

// ---- test helpers (stable across sdk versions) ----
pub fn valid_attestation_id() -> <Test as frame_system::Config>::Hash { sp_core::H256::repeat_byte(0xAA) }
pub fn forged_attestation_id() -> <Test as frame_system::Config>::Hash { sp_core::H256::repeat_byte(0xBB) }
pub fn admitted_crr_id() -> <Test as frame_system::Config>::Hash { sp_core::H256::repeat_byte(0xCC) }
pub fn unadmitted_crr_id() -> <Test as frame_system::Config>::Hash { sp_core::H256::repeat_byte(0xDD) }

pub fn seed_valid_rule_and_attestation(asset: u128, jurisdiction: u16, predicate_passes: bool) {
    RuleRegistry::insert_active_rule_for_test(asset, jurisdiction, predicate_passes, valid_attestation_id());
    RuleRegistry::admit_crr_for_test(admitted_crr_id());
    Verification::record_valid_attestation_for_test(valid_attestation_id());
}

pub fn last_audit_entry_is_rejection() -> bool {
    AuditLog::last_entry_was_rejection()
}
