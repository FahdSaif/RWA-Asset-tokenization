# node/

This directory is populated by `./bootstrap.sh` from the official
polkadot-sdk template. It is intentionally NOT hand-written: `service.rs`,
`command.rs`, `rpc.rs` and `chain_spec.rs` are hundreds of lines of
version-specific glue that must match your pinned polkadot-sdk revision exactly.

After bootstrap:
- edit `chain_spec.rs` to seed genesis with the demo asset, one active rule, and
  the ZK verification key exported from `circuits/export/verification_key.json`.
- everything else you can leave as the template ships it.
