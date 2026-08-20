#!/usr/bin/env bash
# Bootstrap the parts that must come from upstream rather than be hand-written.
set -euo pipefail

echo ">> This fetches the official Substrate/polkadot-sdk node+runtime template."
echo ">> The pallets/ in this repo are yours; node/ and runtime/ are scaffolding."
echo

# Pick ONE template and pin a tag. The minimal template is the least to wade
# through; the parachain template if you need relay-chain integration later.
#   https://github.com/paritytech/polkadot-sdk-minimal-template
#   https://github.com/paritytech/polkadot-sdk-solochain-template
TEMPLATE_REPO="https://github.com/paritytech/polkadot-sdk-solochain-template"
TEMPLATE_TAG="${TEMPLATE_TAG:-master}"   # replace with a real release tag before you rely on it

if [ ! -f node/src/main.rs ] || [ ! -f runtime/src/lib.rs.template ]; then
  tmp=$(mktemp -d)
  git clone --depth 1 --branch "$TEMPLATE_TAG" "$TEMPLATE_REPO" "$tmp"
  # Copy node + runtime skeletons in, without clobbering our pallet wiring notes.
  cp -rn "$tmp/node/." node/ 2>/dev/null || true
  cp -rn "$tmp/runtime/." runtime/ 2>/dev/null || true
  echo ">> Template copied. Now open runtime/src/lib.rs and register the ARCA pallets"
  echo "   (see runtime/src/lib.rs.template in this repo for the construct_runtime! block)."
  rm -rf "$tmp"
fi

# Python
python -m venv .venv && . .venv/bin/activate
pip install -r compliance-ai/requirements.txt -r experiments/requirements.txt

# Circuit tooling
( cd circuits && npm install )

echo ">> Done. Next: match pallet deps in Cargo.toml files to the template's polkadot-sdk version."
