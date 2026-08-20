#!/usr/bin/env bash
# Groth16 trusted setup. Fine for a research prototype; a real deployment needs a
# proper multi-party ceremony. Say so in your limitations.
set -euo pipefail
cd "$(dirname "$0")/.."
PTAU=build/pot12_final.ptau
if [ ! -f "$PTAU" ]; then
  snarkjs powersoftau new bn128 12 build/pot12_0000.ptau -v
  snarkjs powersoftau contribute build/pot12_0000.ptau build/pot12_0001.ptau --name="arca" -v -e="$(head -c32 /dev/urandom | base64)"
  snarkjs powersoftau prepare phase2 build/pot12_0001.ptau "$PTAU" -v
fi
snarkjs groth16 setup build/accreditation.r1cs "$PTAU" build/accreditation_0000.zkey
snarkjs zkey contribute build/accreditation_0000.zkey build/accreditation_final.zkey --name="arca2" -v -e="$(head -c32 /dev/urandom | base64)"
snarkjs zkey export verificationkey build/accreditation_final.zkey export/verification_key.json
echo "vk -> export/verification_key.json  (bake this into the runtime genesis)"
