const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("RWAToken - Functionality Tests", function () {
  let RWAToken;
  let token;
  let owner;
  let minter;
  let user1;
  let user2;
  
  beforeEach(async function () {
    // Deploy the token contract
    RWAToken = await ethers.getContractFactory("RWAToken");
    [owner, minter, user1, user2] = await ethers.getSigners();
    
    token = await RWAToken.deploy("Real World Asset", "RWA");
    await token.deployed();
    
    // Setup roles
    const minterRole = await token.MINTER_ROLE();
    const complianceRole = await token.COMPLIANCE_ROLE();
    
    await token.grantRole(minterRole, minter.address);
    await token.grantRole(complianceRole, owner.address);
    
    // Whitelist users
    await token.setWhitelistStatus(user1.address, true);
  });
  
  it("Should mint a token with correct metadata", async function () {
    // Whitelist the minter for receiving tokens
    await token.setWhitelistStatus(minter.address, true);
    
    const tokenId = 1;
    const tokenURI = "https://example.com/metadata/1";
    const assetClass = "REAL_ESTATE";
    const jurisdiction = "US";
    const validUntil = Math.floor(Date.now() / 1000) + 365 * 24 * 60 * 60; // 1 year
    
    await token.connect(minter).mint(
      minter.address,
      tokenId,
      tokenURI,
      assetClass,
      jurisdiction,
      validUntil,
      owner.address
    );
    
    expect(await token.ownerOf(tokenId)).to.equal(minter.address);
    expect(await token.tokenURI(tokenId)).to.equal(tokenURI);
  });
  
  it("Should allow transfers between whitelisted addresses", async function () {
    // Whitelist the minter and user1
    await token.setWhitelistStatus(minter.address, true);
    await token.setWhitelistStatus(user1.address, true);
    
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
    
    // Transfer token
    await token.connect(minter).transferFrom(minter.address, user1.address, tokenId);
    
    expect(await token.ownerOf(tokenId)).to.equal(user1.address);
  });
  
  it("Should prevent transfers to non-whitelisted addresses", async function () {
    // Whitelist the minter but not user2
    await token.setWhitelistStatus(minter.address, true);
    
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
    
    // Attempt transfer to non-whitelisted address
    await expect(
      token.connect(minter).transferFrom(minter.address, user2.address, tokenId)
    ).to.be.revertedWith("Recipient not whitelisted");
  });
});
