#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build
circom src/accreditation.circom --r1cs --wasm --sym -o build
echo "compiled -> build/accreditation.r1cs, build/accreditation_js/"
