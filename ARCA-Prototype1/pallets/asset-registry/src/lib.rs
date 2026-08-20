//! ARCA — Asset Registry (Layer 4, thin). Authoritative per-asset metadata:
//! type, issuing jurisdiction, applicable rule references. Kept minimal for the
//! single-asset slice; the tx-validation pallet's OwnerOf stands in for the token
//! standard itself in this build.
#![cfg_attr(not(feature = "std"), no_std)]
pub use pallet::*;

#[frame_support::pallet]
pub mod pallet {
    use frame_support::pallet_prelude::*;

    #[pallet::config]
    pub trait Config: frame_system::Config {}

    #[pallet::pallet]
    pub struct Pallet<T>(_);

    #[derive(Clone, Encode, Decode, PartialEq, RuntimeDebug, TypeInfo, MaxEncodedLen)]
    pub struct AssetMeta {
        pub asset_type: u8,      // 0=real-estate, 1=commodity, 2=financial-instrument
        pub jurisdiction: u16,
    }

    #[pallet::storage]
    pub type Meta<T: Config> = StorageMap<_, Blake2_128Concat, u128, AssetMeta>;

    impl<T: Config> Pallet<T> {
        pub fn meta(asset_id: u128) -> Option<AssetMeta> { Meta::<T>::get(asset_id) }
        pub fn register(asset_id: u128, meta: AssetMeta) { Meta::<T>::insert(asset_id, meta); }
    }
}
