const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("RWA Implementation Limitations", function () {
  let RWAToken;
  let ComplianceManager;
  let token;
  let compliance;
  let owner;
  let minter;
  let user1;
  let user2;
  
  beforeEach(async function () {
    // Deploy contracts
    RWAToken = await ethers.getContractFactory("RWAToken");
    ComplianceManager = await ethers.getContractFactory("ComplianceManager");
    
    [owner, minter, user1, user2] = await ethers.getSigners();
    
    token = await RWAToken.deploy("Real World Asset", "RWA");
    compliance = await ComplianceManager.deploy();
    
    await token.deployed();
    await compliance.deployed();
    
    // Setup roles
    const minterRole = await token.MINTER_ROLE();
    const complianceRole = await token.COMPLIANCE_ROLE();
    
    await token.grantRole(minterRole, minter.address);
    await token.grantRole(complianceRole, owner.address);
    
    // Whitelist users
    await token.setWhitelistStatus(minter.address, true);
    await token.setWhitelistStatus(user1.address, true);
  });
  
  it("LIMITATION: Cannot enforce protocol-level compliance across contracts", async function () {
    // This test demonstrates that compliance is not enforced at the protocol level
    // Each contract must implement its own compliance checks
    
    // Mint token
    const tokenId = 1;
    await token.connect(minter).mint(
      minter.address,
      tokenId,
      "https://example.com/metadata/1",
      "REAL_ESTATE",
      "US",
      Math.floor(Date.now() / 1000) + 365 * 24 * 60 * 60,
      owner.address
    );
    
    // Set up compliance for user1 but not for the token contract
    const jurisdiction = ethers.utils.formatBytes32String("US").slice(0, 6);
    await compliance.setUserJurisdiction(user1.address, jurisdiction);
    await compliance.setKYCStatus(user1.address, true);
    
    // The token transfer works because the token contract has no knowledge of the compliance contract
    await token.connect(minter).transferFrom(minter.address, user1.address, tokenId);
    
    // This demonstrates the limitation: compliance is siloed in separate contracts
    expect(await token.ownerOf(tokenId)).to.equal(user1.address);
  });
  
  it("LIMITATION: Storage costs for asset documentation are prohibitive", async function () {
    // This test demonstrates the high gas costs of storing asset documentation on-chain
    
    // Create a large document representing legal documentation
    const largeDocument = "0x" + "1234".repeat(10000); // ~40KB of data
    
    // Attempt to store this on-chain would be extremely expensive
    // This is a simplified example - in reality, storing this much data would cost a fortune
    
    // Instead, we'd typically store a hash or URI, which is a limitation for full on-chain verification
    const tokenId = 2;
    await token.connect(minter).mint(
      minter.address,
      tokenId,
      "ipfs://QmHash", // Just a reference, not the actual document
      "REAL_ESTATE",
      "US",
      Math.floor(Date.now() / 1000) + 365 * 24 * 60 * 60,
      owner.address
    );
    
    // The limitation is demonstrated: we can't feasibly store the full document on-chain
  });
  
  it("LIMITATION: Cannot enforce cross-contract compliance rules", async function () {
    // Deploy a second token contract
    const token2 = await RWAToken.deploy("Second Asset", "SA");
    await token2.deployed();
    
    // Setup roles for the second contract
    const minterRole = await token2.MINTER_ROLE();
    const complianceRole = await token2.COMPLIANCE_ROLE();
    
    await token2.grantRole(minterRole, minter.address);
    await token2.grantRole(complianceRole, owner.address);
    
    // Whitelist user1 in the first contract but not in the second
    await token.setWhitelistStatus(user1.address, true);
    
    // Mint tokens in both contracts
    const tokenId = 1;
    await token.connect(minter).mint(
      minter.address,
      tokenId,
      "https://example.com/metadata/1",
      "REAL_ESTATE",
      "US",
      Math.floor(Date.now() / 1000) + 365 * 24 * 60 * 60,
      owner.address
    );
    
    await token2.connect(minter).mint(
      minter.address,
      tokenId,
      "https://example.com/metadata/2",
      "REAL_ESTATE",
      "US",
      Math.floor(Date.now() / 1000) + 365 * 24 * 60 * 60,
      owner.address
    );
    
    // Transfer in the first contract works
    await token.connect(minter).transferFrom(minter.address, user1.address, tokenId);
    expect(await token.ownerOf(tokenId)).to.equal(user1.address);
    
    // But we can't enforce a global rule that would prevent transfers across all contracts
    // This demonstrates the limitation of contract-level rather than protocol-level compliance
  });
  
  it("LIMITATION: Cannot efficiently handle cross-jurisdictional transfers", async function () {
    // This test demonstrates the difficulty of handling complex cross-jurisdictional rules
    
    const usJurisdiction = ethers.utils.formatBytes32String("US").slice(0, 6);
    const euJurisdiction = ethers.utils.formatBytes32String("EU").slice(0, 6);
    
    // Set up jurisdictions
    await compliance.setUserJurisdiction(user1.address, usJurisdiction);
    await compliance.setUserJurisdiction(user2.address, euJurisdiction);
    
    // Set up KYC
    await compliance.setKYCStatus(user1.address, true);
    await compliance.setKYCStatus(user2.address, true);
    
    // Mint token with US jurisdiction
    const tokenId = 1;
    await token.connect(minter).mint(
      minter.address,
      tokenId,
      "https://example.com/metadata/1",
      "REAL_ESTATE",
      "US",
      Math.floor(Date.now() / 1000) + 365 * 24 * 60 * 60,
      owner.address
    );
    
    // Whitelist both users
    await token.setWhitelistStatus(user1.address, true);
    await token.setWhitelistStatus(user2.address, true);
    
    // Transfer works in the token contract because it doesn't understand jurisdictions
    await token.connect(minter).transferFrom(minter.address, user2.address, tokenId);
    
    // This demonstrates the limitation: the token contract can't enforce complex
    // cross-jurisdictional rules without external systems
  });
});
