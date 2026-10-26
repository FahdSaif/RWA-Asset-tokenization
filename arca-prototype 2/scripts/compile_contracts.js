// Compiles arca/layer3_runtime/contracts/*.sol using the `solc` npm package
// (bundled compiler binary — no network fetch required at compile time,
// which is why this repo pins solc via npm rather than py-solc-x / solc-select,
// both of which need to download a platform solc binary from
// binaries.soliditylang.org at install time).
//
// Output: arca/layer3_runtime/contracts/build/contracts.json
//   { "<ContractName>": { "abi": [...], "bytecode": "0x..." }, ... }
//
// Run: node scripts/compile_contracts.js   (or: npm run compile)

const fs = require("fs");
const path = require("path");
const solc = require("solc");

const CONTRACTS_DIR = path.join(__dirname, "..", "arca", "layer3_runtime", "contracts");
const BUILD_DIR = path.join(CONTRACTS_DIR, "build");

const ENTRY_FILES = ["ComplianceRegistry.sol", "ComplianceToken.sol", "PlainToken.sol"];

function findImports(importPath) {
  const resolved = path.join(CONTRACTS_DIR, importPath);
  if (fs.existsSync(resolved)) {
    return { contents: fs.readFileSync(resolved, "utf8") };
  }
  return { error: `File not found: ${importPath}` };
}

const sources = {};
for (const file of ENTRY_FILES) {
  sources[file] = { content: fs.readFileSync(path.join(CONTRACTS_DIR, file), "utf8") };
}

const input = {
  language: "Solidity",
  sources,
  settings: {
    optimizer: { enabled: true, runs: 200 },
    outputSelection: {
      "*": { "*": ["abi", "evm.bytecode.object", "evm.deployedBytecode.object"] },
    },
  },
};

const output = JSON.parse(solc.compile(JSON.stringify(input), { import: findImports }));

let hasError = false;
if (output.errors) {
  for (const err of output.errors) {
    console.log(`[solc ${err.severity}] ${err.formattedMessage}`);
    if (err.severity === "error") hasError = true;
  }
}
if (hasError) {
  process.exit(1);
}

const artifacts = {};
for (const file of Object.keys(output.contracts)) {
  for (const contractName of Object.keys(output.contracts[file])) {
    const c = output.contracts[file][contractName];
    artifacts[contractName] = {
      abi: c.abi,
      bytecode: "0x" + c.evm.bytecode.object,
      deployedBytecode: "0x" + c.evm.deployedBytecode.object,
      sourceFile: file,
    };
  }
}

fs.mkdirSync(BUILD_DIR, { recursive: true });
const outPath = path.join(BUILD_DIR, "contracts.json");
fs.writeFileSync(outPath, JSON.stringify(artifacts, null, 2));
console.log(`Wrote compiled artifacts for [${Object.keys(artifacts).join(", ")}] to ${outPath}`);
