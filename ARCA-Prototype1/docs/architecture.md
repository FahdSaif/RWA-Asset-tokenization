# Architecture notes

The repo implements a vertical slice, not the whole paper. The slice is chosen so
that the three load-bearing claims are each backed by running code:

1. Non-bypassability — the transfer dispatchable is the only ownership-changing
   path, and it runs the full validation pipeline inside consensus. A raw
   extrinsic gets the same treatment as a client call.
2. AI ≠ enforcement — a CRR is signed by the agent and must clear the governance
   gate before the rule registry will admit it. Unsigned/tampered/rejected CRRs
   stop here.
3. Privacy — the accreditation predicate is proven in zero knowledge; the
   sensitive figure (net_assets) is a private witness.

Deliberately thin: DID/VC identity (reduced to an authorized-issuer key), the
on-chain Groth16 pairing check (storage record is real; the verify is a marked
TODO), full governance deliberation, multi-jurisdiction rule sets, cross-chain.
Each is a paper future-work item, not an oversight.
