//! ARCA — Compliance Rule Registry (Layer 3/4).
//!
//! Holds the ACTIVE rule set as predicates keyed by (asset, jurisdiction), and
//! the set of CRRs that have cleared the governance gate. The tx-validation pallet
//! reads both. Rules only enter here via governance (see the governance pallet);
//! the `*_for_test` helpers below bypass that ONLY under cfg(test).
#![cfg_attr(not(feature = "std"), no_std)]
pub use pallet::*;

#[frame_support::pallet]
pub mod pallet {
    use frame_support::pallet_prelude::*;
    use frame_system::pallet_prelude::*;

    #[pallet::config]
    pub trait Config: frame_system::Config {
        type RuntimeEvent: From<Event<Self>> + IsType<<Self as frame_system::Config>::RuntimeEvent>;
    }

    #[pallet::pallet]
    pub struct Pallet<T>(_);

    /// A compliance rule as a predicate over attested facts. Kept intentionally
    /// small for the single-predicate demo: it just remembers whether the attested
    /// value satisfies the threshold, plus which attestation it is bound to.
    #[derive(Clone, Encode, Decode, PartialEq, RuntimeDebug, TypeInfo, MaxEncodedLen)]
    pub struct Rule<Hash> {
        pub predicate_passes: bool,
        pub bound_attestation: Hash,
    }
    impl<Hash: PartialEq> Rule<Hash> {
        pub fn evaluate(&self, attestation: &Hash) -> bool {
            self.predicate_passes && &self.bound_attestation == attestation
        }
    }

    #[pallet::storage]
    pub type ActiveRule<T: Config> =
        StorageMap<_, Blake2_128Concat, (u128, u16), Rule<T::Hash>>;

    #[pallet::storage]
    pub type AdmittedCrr<T: Config> = StorageMap<_, Blake2_128Concat, T::Hash, ()>;

    #[pallet::event]
    #[pallet::generate_deposit(pub(super) fn deposit_event)]
    pub enum Event<T: Config> {
        RuleActivated { asset_id: u128, jurisdiction: u16 },
        CrrAdmitted { crr_id: T::Hash },
    }

    impl<T: Config> Pallet<T> {
        pub fn active_rule(asset_id: u128, jurisdiction: u16) -> Option<Rule<T::Hash>> {
            ActiveRule::<T>::get((asset_id, jurisdiction))
        }
        pub fn crr_is_admitted(crr_id: &T::Hash) -> bool {
            AdmittedCrr::<T>::contains_key(crr_id)
        }

        /// Called by the governance pallet AFTER signature validation. Not a
        /// dispatchable: rules cannot be pushed by an arbitrary extrinsic.
        pub fn activate_rule(asset_id: u128, jurisdiction: u16, rule: Rule<T::Hash>) {
            ActiveRule::<T>::insert((asset_id, jurisdiction), rule);
            Self::deposit_event(Event::RuleActivated { asset_id, jurisdiction });
        }
        pub fn admit_crr(crr_id: T::Hash) {
            AdmittedCrr::<T>::insert(crr_id, ());
            Self::deposit_event(Event::CrrAdmitted { crr_id });
        }

        #[cfg(test)]
        pub fn insert_active_rule_for_test(asset: u128, j: u16, passes: bool, att: T::Hash) {
            ActiveRule::<T>::insert((asset, j), Rule { predicate_passes: passes, bound_attestation: att });
        }
        #[cfg(test)]
        pub fn admit_crr_for_test(id: T::Hash) { AdmittedCrr::<T>::insert(id, ()); }
    }
}
