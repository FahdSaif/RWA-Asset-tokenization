const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("ComplianceManager - Functionality Tests", function () {
  let ComplianceManager;
  let compliance;
  let owner;
  let admin;
  let user1;
  let user2;
  
  beforeEach(async function () {
    ComplianceManager = await ethers.getContractFactory("ComplianceManager");
    [owner, admin, user1, user2] = await ethers.getSigners();
    
    compliance = await ComplianceManager.deploy();
    await compliance.deployed();
    
    // Setup roles
    const complianceAdminRole = await compliance.COMPLIANCE_ADMIN();
    await compliance.grantRole(complianceAdminRole, admin.address);
  });
  
  it("Should set and retrieve user jurisdiction", async function () {
    const jurisdiction = ethers.utils.formatBytes32String("US").slice(0, 6); // Convert to bytes2
    
    await compliance.connect(admin).setUserJurisdiction(user1.address, jurisdiction);
    
    expect(await compliance.userJurisdiction(user1.address)).to.equal(jurisdiction);
  });
  
  it("Should set KYC status", async function () {
    await compliance.connect(admin).setKYCStatus(user1.address, true);
    
    expect(await compliance.kycVerified(user1.address)).to.equal(true);
  });
  
  it("Should enforce jurisdiction restrictions", async function () {
    const restrictedJurisdiction = ethers.utils.formatBytes32String("CN").slice(0, 6);
    const allowedJurisdiction = ethers.utils.formatBytes32String("US").slice(0, 6);
    
    // Set jurisdictions
    await compliance.connect(admin).setUserJurisdiction(user1.address, allowedJurisdiction);
    await compliance.connect(admin).setUserJurisdiction(user2.address, restrictedJurisdiction);
    
    // Set KYC status
    await compliance.connect(admin).setKYCStatus(user1.address, true);
    await compliance.connect(admin).setKYCStatus(user2.address, true);
    
    // Restrict a jurisdiction
    await compliance.connect(admin).setJurisdictionRestriction(restrictedJurisdiction, true);
    
    // Check compliance
    expect(await compliance.checkCompliance(user1.address, user1.address, 1000)).to.equal(true);
    expect(await compliance.checkCompliance(user1.address, user2.address, 1000)).to.equal(false);
  });
});
