<img width="5705" height="5192" alt="image" src="https://github.com/user-attachments/assets/417c010c-e116-470d-a5ec-efbd5874d2bf" />


sequenceDiagram
    %% === Participants ===
    actor Issuer as Asset Issuer / Project
    participant LO as Legal Officer (Judicial Officer)
    participant LNode as Logion Node (Substrate Runtime)
    participant IPFS as Private Encrypted IPFS Cluster
    participant ZKP as ZKP Prover/Verifier
    participant TokenChain as Token Chain (any chain)
    actor Investor as Investor / Buyer
    participant Registry as Land/Asset Registry or Court

    %% === 0. Onboarding & Identity ===
    Issuer->>LO: Request onboarding & KYC/Identity verification
    LO->>LNode: Create Legal Officer Case (LOC) request
    LNode-->>LO: LOC ID issueda (pending)
    LO-->>Issuer: Request supporting documents & declarations

    %% === 1. Evidence Collection & Sealing ===
    Issuer->>LO: Submit asset docs (titles, contracts, appraisals)
    LO->>IPFS: Encrypt & pin evidence (private cluster)
    IPFS-->>LO: Content IDs (CIDs) for encrypted files
    LO->>ZKP: Generate commitment/proof (no raw data revealed)
    ZKP-->>LO: ZK proof artifact (attesting to evidence integrity)

    %% === 2. LOC Finalization & Certificate ===
    LO->>LNode: Attach CIDs + ZK proof + identity attestations to LOC
    LNode-->>LO: LOC finalized (immutable reference on chain)
    note right of LNode: LOC contains:<br/>• Issuer identity binding<br/>• Evidence references (CIDs)<br/>• ZK proof commitments<br/>• Legal Officer signatures
    LO->>LNode: Request Public Certificate issuance
    LNode-->>LO: Public Certificate URL/hash (verifiable on-chain)
    LO-->>Issuer: Deliver Logion Certificate (linking token↔legal evidence)

    %% === 3. Token Mint (on chosen chain) ===
    Issuer->>TokenChain: Mint RWA token/NFT (metadata ↔ LOC/Certificate refs)
    TokenChain-->>Issuer: Token ID(s) minted
    note right of TokenChain: Token metadata stores:<br/>• LOC ID / Cert hash<br/>• Optional jurisdiction/terms<br/>• Off-chain doc pointers (CIDs via gateway)

    %% === 4. Primary Sale ===
    Issuer->>Investor: Offer token (primary sale terms)
    Investor->>TokenChain: Purchase / receive token
    TokenChain-->>Investor: Transfer confirmed

    %% === 5. Secondary Market Transfer (with verification) ===
    Investor->>TokenChain: Initiate transfer/listing
    TokenChain->>LNode: (Optional) Verify certificate & LOC status
    LNode->>ZKP: Verify proofs still valid (no data leakage)
    ZKP-->>LNode: Proof verified / not verified
    alt Valid & active
        LNode-->>TokenChain: Attestation: Certificate/LOC OK
        TokenChain-->>Investor: Transfer completes
    else Revoked/expired/flagged
        LNode-->>TokenChain: Attestation: Not OK (halt/flag)
        TokenChain-->>Investor: Transfer blocked or requires remediation
    end

    %% === 6. Corporate Actions / Updates ===
    Issuer->>LO: Submit updates (renewals, new docs, events)
    LO->>IPFS: Encrypt & pin updated evidence
    LO->>ZKP: Generate updated proofs
    LO->>LNode: Update LOC (new CIDs + proofs + signatures)
    LNode-->>TokenChain: (Optional) Emit status/event webhook

    %% === 7. Redemption / Burn ===
    Investor->>Issuer: Request redemption / settlement
    Issuer->>TokenChain: Burn or lock token pending settlement
    Issuer->>Registry: Off-chain title/claim transfer
    Registry-->>Issuer: Title updated / settlement confirmation
    Issuer-->>Investor: Deliver off-chain rights / consideration

    %% === 8. Dispute / Enforcement (if needed) ===
    Investor->>LO: File dispute referencing Certificate & LOC
    LO->>LNode: Retrieve verifiable state (LOC + timestamps)
    LO->>Registry: Present certified evidence in proceedings
    Registry-->>LO: Ruling / order
    LO->>LNode: Record outcome (e.g., revoke, annotate, or uphold)
    LNode-->>TokenChain: (Optional) Notify state change for market integrity
