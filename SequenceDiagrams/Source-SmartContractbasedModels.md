sequenceDiagram
actor U as User/Wallet App
participant A as dApp Backend (optional)
participant SC as Smart Contract
participant K as KYC/AML Oracle
participant J as Jurisdiction Rules Engine
participant L1 as Blockchain (Ethereum/Solana)

U->>A: (1) Initiate transfer(recipient, amount, token)
alt (2) Application Layer Enforcement
    note right of A: (3) Can be bypassed / upgraded / misconfigured
    A->>K: (4) Verify KYC/AML(User, Recipient)
    A->>J: (5) Check jurisdictional restrictions
    A-->>U: (6) Return OK / Reject
    U->>SC: (7) executeTransfer(token, amount, recipient)
else (8) Smart Contract Layer Enforcement
    note right of SC: (9) Defined by developers<br/>Implementation at smart contract layer
    U->>SC: (10) executeTransfer(token, amount, recipient)
    SC->>K: (11) requestKYCStatus(sender, recipient)
    K-->>SC: (12) KYC/AML status
    SC->>J: (13) requestJurisdictionDecision(sender, recipient, asset)
    J-->>SC: (14) ALLOW / DENY / REQUIRE_ESCROW
    SC->>SC: (15) Apply compliance logic (developer-defined)
    alt (16) Denied
        SC-->>U: (17) revert("Compliance failed")
    else (18) Allowed
        SC->>L1: (19) Commit transaction to blockchain
        L1-->>U: (20) Transaction receipt
    end
end
