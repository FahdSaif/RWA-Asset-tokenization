//! ARCA — Verification & Identity (Layer 2).
//!
//! In the full design this verifies a Groth16 proof on-chain (arkworks) against a
//! verification key bound to an authorized issuer, then records the attestation.
//! For the vertical slice we keep the ON-CHAIN RECORD real (the tx-validation
//! pallet genuinely checks it) but leave the pairing check as a clearly-marked
//! TODO so the slice runs without dragging in the full crypto stack on day one.
#![cfg_attr(not(feature = "std"), no_std)]
pub use pallet::*;

#[frame_support::pallet]
pub mod pallet {
    use frame_support::pallet_prelude::*;

    #[pallet::config]
    pub trait Config: frame_system::Config {
        type RuntimeEvent: From<Event<Self>> + IsType<<Self as frame_system::Config>::RuntimeEvent>;
    }

    #[pallet::pallet]
    pub struct Pallet<T>(_);

    /// attestation_id -> valid
    #[pallet::storage]
    pub type ValidAttestation<T: Config> = StorageMap<_, Blake2_128Concat, T::Hash, ()>;

    /// authorized issuer public keys (thin DID stub)
    #[pallet::storage]
    pub type AuthorizedIssuer<T: Config> = StorageMap<_, Blake2_128Concat, T::Hash, ()>;

    #[pallet::event]
    #[pallet::generate_deposit(pub(super) fn deposit_event)]
    pub enum Event<T: Config> {
        AttestationRecorded { id: T::Hash },
    }

    impl<T: Config> Pallet<T> {
        pub fn is_attestation_valid(id: &T::Hash) -> bool {
            ValidAttestation::<T>::contains_key(id)
        }

        /// Verify + record. Replace the TODO with an arkworks Groth16 verify against
        /// the issuer-bound vk; keep the storage write, which is what enforcement reads.
        pub fn verify_and_record(id: T::Hash, _proof: &[u8], _public_inputs: &[u8]) -> bool {
            // TODO(zk): groth16_verify(vk, proof, public_inputs) -> bool
            let ok = true; // slice: attestation presence is what the demo exercises
            if ok {
                ValidAttestation::<T>::insert(id, ());
                Self::deposit_event(Event::AttestationRecorded { id });
            }
            ok
        }

        #[cfg(test)]
        pub fn record_valid_attestation_for_test(id: T::Hash) { ValidAttestation::<T>::insert(id, ()); }
    }
}
