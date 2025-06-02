# 🔗 On-Chain Data for Automobile Asset Tokenization

This document outlines the key fields stored **directly on the blockchain** when tokenizing an automobile as a digital asset. These data points are immutable, verifiable, and play a critical role in trustless ownership, transferability, and compliance.

---

##  Visual Overview

![onchain](https://github.com/user-attachments/assets/6b70f6aa-53d2-40bb-b3d9-8f000f0f5317)


---

##  Smart Contract Data Fields

### 1.  Asset ID
- Unique identifier (e.g. ERC-721 token ID)
- Links the digital token to the physical vehicle

### 2.  VIN Hash
- Hashed version of the Vehicle Identification Number (VIN)
- Ensures proof of link without exposing raw identity

### 3.  Year
- Manufacturing or model year
- Helps determine valuation, depreciation, and eligibility

### 4.  Make & Model
- Brand + model name (e.g. Tesla Model 3)
- Included for visual/reference metadata

### 5.  Fraction ID (if fractionalized)
- Unique sub-token or series identifier (e.g. ERC-1155 or ERC-1400)
- Enables shared or partial ownership of the vehicle

### 6.  Ownership
- Ethereum address(es) of current token holder(s)
- Decentralized control and transfer logic

### 7.  Compliance Tag
- Flags for regulatory readiness or market fit
  - e.g. "US Road Legal", "EU Compliant", "DeFi Transferable"

---

## ✨ Why Store These On-Chain?

| Field           | Reason for On-Chain Storage                      |
|------------------|--------------------------------------------------|
| Asset ID         | Token anchor and registry                       |
| VIN Hash         | Verifiable proof of linkage to physical car     |
| Ownership        | Enables permissionless transfers or restrictions|
| Compliance Tag   | Can be used in transfer or access control logic |
| Fraction ID      | Facilitates shared ownership models             |

---

## 🔐 Security & Design Notes

- Avoid storing raw VINs — hash them before storage.
- Token metadata should be extensible (e.g. ERC-721 Metadata URI).
- Compliance tags can be encoded as enums or mappings.
- All user-generated or market-sensitive data should be hashed or kept off-chain.

---

## 📁 Related Diagrams

- [Off-Chain Data →](./off-chain-data.md)
- [Blockchain Block Format →](./block-structure-automobile.md)

---

*Last updated: {{TODAY}}*
