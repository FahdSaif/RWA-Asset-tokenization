sequenceDiagram
  title: Comparative Enforcement Flow
  participant U as User
  participant SC as Smart Contract
  participant P as Protocol Layer

  %% Smart Contract-Based
  Note over U,SC: Application-Layer (Smart Contract–Based)
  U->>SC: (1) requestTransfer()
  SC-->>U: (2) ack(received)
  SC->>SC: (3) checkCompliance()  %% bypassable
  SC-->>U: (4) transferExecuted()

  %% Protocol-Level
  Note over SC,P: Protocol-Layer (Proposed Runtime)
  SC->>P: (5) verifyComplianceAtProtocol()
  P-->>SC: (6) enforceKYCandJurisdiction()
  SC-->>U: (7) transferFinalized(non-bypassable)
