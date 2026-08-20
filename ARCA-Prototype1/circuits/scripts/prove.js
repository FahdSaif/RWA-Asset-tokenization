// Generate a proof for the accreditation predicate and time it.
// Usage: node scripts/prove.js <net_assets> <threshold>
const snarkjs = require("snarkjs");
const fs = require("fs");
const path = require("path");

async function main() {
  const net_assets = BigInt(process.argv[2] ?? "1500000");
  const threshold  = BigInt(process.argv[3] ?? "1000000");
  const wasm = path.join(__dirname, "..", "build", "accreditation_js", "accreditation.wasm");
  const zkey = path.join(__dirname, "..", "build", "accreditation_final.zkey");

  const t0 = process.hrtime.bigint();
  const { proof, publicSignals } = await snarkjs.groth16.fullProve(
    { net_assets: net_assets.toString(), threshold: threshold.toString() },
    wasm, zkey
  );
  const t1 = process.hrtime.bigint();

  const out = path.join(__dirname, "..", "build", "proof.json");
  fs.writeFileSync(out, JSON.stringify({ proof, publicSignals }, null, 2));
  const ms = Number(t1 - t0) / 1e6;
  console.log(JSON.stringify({ prove_ms: ms, proof_size_bytes: Buffer.byteLength(JSON.stringify(proof)), publicSignals }));
}
main().then(() => process.exit(0));
