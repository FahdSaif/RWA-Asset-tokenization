sequenceDiagram
  title: Universal RWA Compliance Workflow (Template)
  participant U as User
  participant SC as Smart Contract
  participant K as KYC Oracle
  participant J as Jurisdiction Engine
  participant O as Price/State Oracle
  participant R as Regulator/Audit Node
  participant DAO as Governance DAO
  participant DB as Compliance Log DB

  rect lightgray
  %% Phase: Initialization & Input
  U->>SC: (1) submitRequest(operation, asset, amount, recipient)
  SC-->>U: (2) ack(received)
  end

  rect lightyellow
  %% Phase: KYC & Identity
  SC->>K: (3) verifyKYC(sender, recipient)
  K-->>SC: (4) kycResult(verified / failed, ref)
  end

  rect lightblue
  %% Phase: Jurisdiction & Policy
  SC->>J: (5) evaluatePolicy(asset, parties, amount)
  J-->>SC: (6) policyDecision(ALLOW / DENY / REQUIRE_ESCROW / LIMITS)
  end

  rect lightgreen
  %% Phase: Oracle & Data Validation
  SC->>O: (7) fetchMarketState(asset)
  O-->>SC: (8) return(price, state, proof)
  end

  rect white
  %% Phase: Execution & Settlement
  SC->>SC: (9) enforceCompliance(kyc, policy, oracle)
  SC->>SC: (10) routeSettlement(escrowRequired?)
  SC-->>U: (11) confirm(status, txHash)
  end

  rect lightgray
  %% Phase: Audit & Logging
  SC->>R: (12) submitRegAudit(txMeta, zkProofRef)
  R-->>SC: (13) receipt(stored)
  SC->>DB: (14) appendAuditLog(txId, envelopeHash)
  DB-->>SC: (15) ack(indexed)
  end

  rect lightyellow
  %% Phase: Governance Signal (optional)
  SC->>DAO: (16) emitPolicyUsage(event, anonymizedStats)
  DAO-->>SC: (17) receipt(queuedForReview)
  end
