// Verify the proof and time verification.
const snarkjs = require("snarkjs");
const fs = require("fs");
const path = require("path");

async function main() {
  const vk = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "export", "verification_key.json")));
  const { proof, publicSignals } = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "build", "proof.json")));
  const t0 = process.hrtime.bigint();
  const ok = await snarkjs.groth16.verify(vk, publicSignals, proof);
  const t1 = process.hrtime.bigint();
  console.log(JSON.stringify({ verified: ok, verify_ms: Number(t1 - t0) / 1e6 }));
}
main().then(() => process.exit(0));
