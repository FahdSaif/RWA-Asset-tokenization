//! ARCA — Audit Log (Layer 3). Append-only record of every validation outcome.
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

    #[pallet::storage]
    pub type NextIndex<T: Config> = StorageValue<_, u64, ValueQuery>;

    #[pallet::storage]
    pub type LastWasRejection<T: Config> = StorageValue<_, bool, ValueQuery>;

    #[pallet::event]
    #[pallet::generate_deposit(pub(super) fn deposit_event)]
    pub enum Event<T: Config> {
        Recorded { index: u64, accepted: bool, asset_id: u128 },
    }

    impl<T: Config> Pallet<T> {
        /// `stage` is generic-erased to keep this pallet dependency-light; callers
        /// pass a debug string in a fuller build. Here we record the essentials.
        pub fn record<S>(asset_id: u128, accepted: bool, _stage: Option<S>, _zk: T::Hash, _crr: T::Hash) {
            let index = NextIndex::<T>::get();
            NextIndex::<T>::put(index + 1);
            LastWasRejection::<T>::put(!accepted);
            Self::deposit_event(Event::Recorded { index, accepted, asset_id });
        }

        #[cfg(test)]
        pub fn last_entry_was_rejection() -> bool { LastWasRejection::<T>::get() }
    }
}
