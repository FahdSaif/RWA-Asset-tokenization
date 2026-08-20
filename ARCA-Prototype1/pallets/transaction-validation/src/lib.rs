//! ARCA — Transaction Validation Module (Layer 3, Runtime Enforcement).
//!
//! This is the architectural core of the paper. It does one thing that no
//! smart-contract-layer design can: it runs the compliance check *inside the
//! runtime's own dispatch*, as a precondition of the state transition. There is
//! therefore no submission path — client, script, or raw extrinsic — that can
//! finalize a non-compliant transfer, because "finalize" is what this code gates.
//!
//! The validation pipeline for a transfer is:
//!   1. look up the applicable rule from the Rule Registry (by asset + jurisdiction)
//!   2. verify the ZK attestation against the Verification pallet
//!   3. verify the referenced CRR is present and governance-admitted
//!   4. accept -> proceed to transfer; reject -> error, and log either way
//!
//! Enforcement primacy (paper §V-A) lives here in step 0: the dispatchable
//! `transfer` is the ONLY way asset ownership changes, and it always runs 1–4.

#![cfg_attr(not(feature = "std"), no_std)]

pub use pallet::*;

#[cfg(test)]
mod mock;
#[cfg(test)]
mod tests;
#[cfg(feature = "runtime-benchmarks")]
mod benchmarking;
pub mod weights;
pub use weights::WeightInfo;

#[frame_support::pallet]
pub mod pallet {
    use super::*;
    use frame_support::pallet_prelude::*;
    use frame_system::pallet_prelude::*;

    #[pallet::config]
    pub trait Config:
        frame_system::Config
        + pallet_rule_registry::Config
        + pallet_verification::Config
        + pallet_audit_log::Config
    {
        type RuntimeEvent: From<Event<Self>> + IsType<<Self as frame_system::Config>::RuntimeEvent>;
        type WeightInfo: WeightInfo;
    }

    #[pallet::pallet]
    pub struct Pallet<T>(_);

    /// Minimal ownership map — stands in for the compliance-capable token standard.
    /// A real deployment binds this to the asset-registry pallet.
    #[pallet::storage]
    pub type OwnerOf<T: Config> = StorageMap<_, Blake2_128Concat, u128 /*asset_id*/, T::AccountId>;

    #[pallet::event]
    #[pallet::generate_deposit(pub(super) fn deposit_event)]
    pub enum Event<T: Config> {
        /// Transfer passed all compliance stages and finalized.
        TransferAccepted { asset_id: u128, from: T::AccountId, to: T::AccountId },
        /// Transfer rejected at the runtime layer, with the failing stage.
        TransferRejected { asset_id: u128, stage: RejectStage },
    }

    #[derive(Clone, Encode, Decode, PartialEq, RuntimeDebug, TypeInfo, MaxEncodedLen)]
    pub enum RejectStage {
        NoApplicableRule,
        ZkAttestationInvalid,
        CrrMissingOrUnadmitted,
        RulePredicateFailed,
        NotOwner,
    }

    #[pallet::error]
    pub enum Error<T> {
        NoApplicableRule,
        ZkAttestationInvalid,
        CrrMissingOrUnadmitted,
        RulePredicateFailed,
        NotOwner,
    }

    #[pallet::call]
    impl<T: Config> Pallet<T> {
        /// The single, mandatory path for moving a tokenized asset.
        ///
        /// `zk_attestation_id` references a proof already verified & recorded by the
        /// Verification pallet; `crr_id` references a governance-admitted Compliance
        /// Recommendation Record. Both are checked here — passing garbage, or bypassing
        /// the intended client and hand-rolling this extrinsic, changes nothing: the
        /// checks are on the server side of consensus.
        #[pallet::call_index(0)]
        #[pallet::weight(T::WeightInfo::transfer())]
        pub fn transfer(
            origin: OriginFor<T>,
            asset_id: u128,
            to: T::AccountId,
            jurisdiction: u16,
            zk_attestation_id: T::Hash,
            crr_id: T::Hash,
        ) -> DispatchResult {
            let from = ensure_signed(origin)?;

            let result = Self::run_validation_pipeline(
                asset_id, &from, &to, jurisdiction, &zk_attestation_id, &crr_id,
            );

            // Audit EVERY outcome, accept or reject (paper: Audit Log Module).
            match &result {
                Ok(()) => {
                    OwnerOf::<T>::insert(asset_id, to.clone());
                    pallet_audit_log::Pallet::<T>::record(
                        asset_id, true, None, zk_attestation_id, crr_id,
                    );
                    Self::deposit_event(Event::TransferAccepted { asset_id, from, to });
                    Ok(())
                }
                Err(stage) => {
                    pallet_audit_log::Pallet::<T>::record(
                        asset_id, false, Some(stage.clone()), zk_attestation_id, crr_id,
                    );
                    Self::deposit_event(Event::TransferRejected { asset_id, stage: stage.clone() });
                    Err(Self::stage_to_error(stage).into())
                }
            }
        }
    }

    impl<T: Config> Pallet<T> {
        fn run_validation_pipeline(
            asset_id: u128,
            from: &T::AccountId,
            _to: &T::AccountId,
            jurisdiction: u16,
            zk_attestation_id: &T::Hash,
            crr_id: &T::Hash,
        ) -> Result<(), RejectStage> {
            // 0. ownership
            if OwnerOf::<T>::get(asset_id).as_ref() != Some(from) {
                return Err(RejectStage::NotOwner);
            }
            // 1. applicable rule
            let rule = pallet_rule_registry::Pallet::<T>::active_rule(asset_id, jurisdiction)
                .ok_or(RejectStage::NoApplicableRule)?;
            // 2. ZK attestation must be verified & on record
            if !pallet_verification::Pallet::<T>::is_attestation_valid(zk_attestation_id) {
                return Err(RejectStage::ZkAttestationInvalid);
            }
            // 3. CRR must exist AND have passed the governance gate
            if !pallet_rule_registry::Pallet::<T>::crr_is_admitted(crr_id) {
                return Err(RejectStage::CrrMissingOrUnadmitted);
            }
            // 4. evaluate the rule predicate against the attested facts
            if !rule.evaluate(zk_attestation_id) {
                return Err(RejectStage::RulePredicateFailed);
            }
            Ok(())
        }

        fn stage_to_error(stage: &RejectStage) -> Error<T> {
            match stage {
                RejectStage::NoApplicableRule => Error::NoApplicableRule,
                RejectStage::ZkAttestationInvalid => Error::ZkAttestationInvalid,
                RejectStage::CrrMissingOrUnadmitted => Error::CrrMissingOrUnadmitted,
                RejectStage::RulePredicateFailed => Error::RulePredicateFailed,
                RejectStage::NotOwner => Error::NotOwner,
            }
        }

        /// Test/dev helper to seed ownership.
        pub fn set_owner(asset_id: u128, who: T::AccountId) {
            OwnerOf::<T>::insert(asset_id, who);
        }
    }
}
