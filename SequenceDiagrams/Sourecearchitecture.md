graph TB
  %% Architecture — Compliance-Aware RWA Blockchain (Black & White)

  %% ===== Access Layer =====
  subgraph A[Access Layer]
    U[User]
    DApp[dApp / Frontend]
    W[Wallet]
    GW[API or RPC Gateway]
  end

  %% ===== Protocol Runtime Layer =====
  subgraph R[Protocol Runtime Layer]
    ER[Entry Router\nTransaction parsing and routing]
    CE[Compliance Engine\nNon-bypassable rules]
    JE[Jurisdiction Engine\nPolicy and residency checks]
    IV[Identity Verifier\nKYC and AML proofs]
    TLM[Token Lifecycle Manager\nMint, burn, transfer, freeze]
    SE[Settlement or Escrow\nRuntime enforcement]
    GM[Governance DAO\nVoting, proposals, treasury]
    CN[Consensus and Node Services]
  end

  %% ===== Data and Audit Layer =====
  subgraph S[Data and Audit Layer]
    CLD[Compliance Log Database\nImmutable logs and proofs]
    TRG[Token Registry\nAsset IDs and metadata]
    ZKS[ZK Merkle Store\nCommitments and hashes]
  end

  %% ===== External Systems =====
  subgraph X[External or Off-Chain Systems]
    KYC[KYC Providers\nCredentials and attestations]
    ORA[Data Oracles\nPrice, state, proof of reserve]
    REG[Regulator or Audit Node]
    SPV[Legal SPV or Custodian\nTitle and custody]
    BRG[Cross-Chain Bridges]
  end

  %% ---- Access flow ----
  U --> DApp --> W --> GW --> ER

  %% ---- Runtime flows ----
  ER --> CE
  CE --> JE
  CE --> IV
  CE --> TLM
  TLM --> SE
  GM --> CE
  GM --> TLM
  CN --> ER
  CN --> TLM

  %% ---- Data and audit writes ----
  CE --> CLD
  TLM --> TRG
  SE --> ZKS
  CE --> ZKS

  %% ---- External integrations ----
  IV --> KYC
  JE --> SPV
  CE --> REG
  CE --> ORA
  TLM --> BRG

  %% ---- Read paths for oversight ----
  REG --> CLD
  REG --> ZKS
