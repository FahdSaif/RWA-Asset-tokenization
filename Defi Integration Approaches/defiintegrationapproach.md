---
title: "DeFi Integration Approaches"
layout: default
---

# DeFi Integration Approaches

This section investigates and proposes suitable DeFi integration approaches and frameworks for RWA tokenisation. 

## MakerDAO's Collateralisation Framework
MakerDAO pioneered real-world asset integration through its **Multi-Collateral DAI** system, enabling decentralised stablecoin creation backed by diversified asset portfolios including tokenised real estate loans and trade receivables.  
Through partnerships with asset originators and third-party custodians, MakerDAO employs vault structures and risk models to collateralise real-world assets for DAI issuance.  

The **RWA Foundation** and dedicated core units manage governance, legal structuring, and risk assessment. Whilst this approach increases portfolio diversification, it introduces dependencies on off-chain entities. Smart contracts enforce stability fees, liquidation parameters, and oracle price feeds to maintain system solvency.

## Centrifuge's NFT-Based Credit Markets
**Centrifuge** converts off-chain assets including invoices and property contracts into **ERC-721 NFTs**, pooling these within **Tinlake**, a DeFi lending platform issuing interest-bearing tokens (DROP and TIN) to investors.  
- **DROP tokens**: senior, fixed yields.  
- **TIN tokens**: junior, higher-risk tranche.  

This model connects off-chain originators with on-chain liquidity providers, creating transparent, programmable credit markets. Integration with MakerDAO enables NFT collateralisation for DAI minting. Centrifuge’s governance and compliance depend on entity-level identity verification and real-world legal recourse mechanisms.

## Goldfinch's Undercollateralised Lending Model
**Goldfinch** operates a decentralised protocol for undercollateralised lending, using off-chain data such as credit scores and repayment histories for borrower risk assessment. Borrowers undergo evaluation by backers who stake capital on their behalf.  

Loans are pooled and distributed via smart contracts, with repayments redistributed to liquidity providers. The protocol combines DeFi transparency with traditional credit underwriting through borrower identification, business verification, and tiered risk tranching. Goldfinch demonstrates the integration of conventional creditworthiness assessment with decentralised capital allocation.

## Maple Finance's Institutional Approach
**Maple Finance** targets institutional lenders through permissioned lending pools where borrowers undergo comprehensive due diligence and pool delegates manage risk exposure. Real-world asset collateral includes tokenised treasury bills, commercial debt, and off-chain receivables.  

Compliance modules and whitelisting ensure institutional compatibility. Maple’s approach introduces DeFi-native loan administration whilst maintaining legal enforceability through smart contract-linked covenants and third-party custodial arrangements.
