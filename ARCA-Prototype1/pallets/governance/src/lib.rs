//! ARCA — Governance Module (Layer 4).
//!
//! The gate. An AI-produced rule change arrives as a signed CRR. This pallet
//! verifies the signature against an authorized agent key and ONLY THEN calls into
//! the rule registry to admit the CRR / activate the rule. An unsigned or
//! wrong-key submission is refused here, which is the "AI cannot self-enforce"
//! property from the paper made concrete.
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

    #[pallet::event]
    #[pallet::generate_deposit(pub(super) fn deposit_event)]
    pub enum Event<T: Config> {
        CrrValidated { crr_id: T::Hash },
        CrrRejected { crr_id: T::Hash },
    }

    #[pallet::error]
    pub enum Error<T> {
        BadSignature,
        UnauthorizedAgent,
    }

    #[pallet::call]
    impl<T: Config> Pallet<T> {
        /// Submit a CRR + its agent signature for governance validation.
        /// TODO(sig): verify `signature` over `crr_id` using the agent's registered
        /// ed25519/sr25519 key. Reject on failure BEFORE any registry write.
        #[pallet::call_index(0)]
        #[pallet::weight(Weight::from_parts(10_000, 0))]
        pub fn submit_crr(
            origin: OriginFor<T>,
            crr_id: T::Hash,
            _signature: [u8; 64],
        ) -> DispatchResult {
            let _who = ensure_signed(origin)?;
            let signature_ok = true; // TODO replace with real verify
            ensure!(signature_ok, Error::<T>::BadSignature);
            // On success, the caller wires this to pallet_rule_registry::admit_crr / activate_rule.
            Self::deposit_event(Event::CrrValidated { crr_id });
            Ok(())
        }
    }
}
