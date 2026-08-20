//! The tests that make the paper's central claim falsifiable.
//!
//! The important one is `raw_bypass_is_still_rejected`: it constructs the transfer
//! WITHOUT going through any application logic — directly at the pallet dispatch,
//! which is exactly what a hand-rolled raw extrinsic does — and shows it is still
//! rejected. That is the whole argument of §V-A / Threat Class I in one assertion.

use crate::{mock::*, Error, RejectStage, Event};
use frame_support::{assert_noop, assert_ok};

const ALICE: u64 = 1;
const BOB: u64 = 2;
const ASSET: u128 = 42;
const JURISDICTION: u16 = 36; // e.g. AU

#[test]
fn compliant_transfer_is_accepted() {
    new_test_ext().execute_with(|| {
        seed_valid_rule_and_attestation(ASSET, JURISDICTION, /*passes=*/true);
        TxValidation::set_owner(ASSET, ALICE);

        assert_ok!(TxValidation::transfer(
            RuntimeOrigin::signed(ALICE),
            ASSET, BOB, JURISDICTION,
            valid_attestation_id(), admitted_crr_id(),
        ));
        assert_eq!(TxValidation::owner_of(ASSET), Some(BOB));
    });
}

#[test]
fn raw_bypass_is_still_rejected() {
    new_test_ext().execute_with(|| {
        // A rule exists and would fail for this party. No client-side check runs;
        // we call the dispatchable directly with a bogus attestation, the way a
        // raw extrinsic submitted straight to the node would.
        seed_valid_rule_and_attestation(ASSET, JURISDICTION, /*passes=*/true);
        TxValidation::set_owner(ASSET, ALICE);

        assert_noop!(
            TxValidation::transfer(
                RuntimeOrigin::signed(ALICE),
                ASSET, BOB, JURISDICTION,
                forged_attestation_id(),   // never verified by the Verification pallet
                admitted_crr_id(),
            ),
            Error::<Test>::ZkAttestationInvalid
        );
        // Ownership did NOT move.
        assert_eq!(TxValidation::owner_of(ASSET), Some(ALICE));
    });
}

#[test]
fn unadmitted_crr_is_rejected() {
    new_test_ext().execute_with(|| {
        seed_valid_rule_and_attestation(ASSET, JURISDICTION, true);
        TxValidation::set_owner(ASSET, ALICE);
        assert_noop!(
            TxValidation::transfer(
                RuntimeOrigin::signed(ALICE),
                ASSET, BOB, JURISDICTION,
                valid_attestation_id(), unadmitted_crr_id(),
            ),
            Error::<Test>::CrrMissingOrUnadmitted
        );
    });
}

#[test]
fn failing_predicate_is_rejected_and_logged() {
    new_test_ext().execute_with(|| {
        seed_valid_rule_and_attestation(ASSET, JURISDICTION, /*passes=*/false);
        TxValidation::set_owner(ASSET, ALICE);
        assert_noop!(
            TxValidation::transfer(
                RuntimeOrigin::signed(ALICE),
                ASSET, BOB, JURISDICTION,
                valid_attestation_id(), admitted_crr_id(),
            ),
            Error::<Test>::RulePredicateFailed
        );
        // audit log recorded a rejection
        assert!(last_audit_entry_is_rejection());
    });
}
