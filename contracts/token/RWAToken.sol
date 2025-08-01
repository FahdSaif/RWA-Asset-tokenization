// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";

/**
 * @title RWAToken
 * @dev Implementation of a Real World Asset token with compliance features
 */
contract RWAToken is ERC721URIStorage, AccessControl {
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant COMPLIANCE_ROLE = keccak256("COMPLIANCE_ROLE");
    
    // Compliance registry mapping
    mapping(address => bool) private _whitelistedAddresses;
    
    // Asset metadata
    struct AssetData {
        string assetClass;
        string jurisdiction;
        uint256 validUntil;
        address custodian;
    }
    
    mapping(uint256 => AssetData) private _assetData;
    
    event ComplianceStatusChanged(address indexed account, bool status);
    event AssetFrozen(uint256 indexed tokenId, string reason);
    
    constructor(string memory name, string memory symbol) 
        ERC721(name, symbol) {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(MINTER_ROLE, msg.sender);
        _grantRole(COMPLIANCE_ROLE, msg.sender);
    }
    
    function mint(
        address to, 
        uint256 tokenId, 
        string memory tokenURI,
        string memory assetClass,
        string memory jurisdiction,
        uint256 validUntil,
        address custodian
    ) public onlyRole(MINTER_ROLE) {
        require(_whitelistedAddresses[to], "Recipient not whitelisted");
        
        _mint(to, tokenId);
        _setTokenURI(tokenId, tokenURI);
        
        _assetData[tokenId] = AssetData({
            assetClass: assetClass,
            jurisdiction: jurisdiction,
            validUntil: validUntil,
            custodian: custodian
        });
    }
    
    function setWhitelistStatus(address account, bool status) 
        public onlyRole(COMPLIANCE_ROLE) {
        _whitelistedAddresses[account] = status;
        emit ComplianceStatusChanged(account, status);
    }
    
    function freezeAsset(uint256 tokenId, string memory reason) 
        public onlyRole(COMPLIANCE_ROLE) {
        emit AssetFrozen(tokenId, reason);
        // Implementation of freeze mechanism
    }
    
    // Override transfer function to enforce compliance
    function _beforeTokenTransfer(
        address from,
        address to,
        uint256 tokenId,
        uint256 batchSize
    ) internal override {
        super._beforeTokenTransfer(from, to, tokenId, batchSize);
        
        if (to != address(0)) { // Skip check for burns
            require(_whitelistedAddresses[to], "Recipient not whitelisted");
            require(block.timestamp <= _assetData[tokenId].validUntil, "Asset expired");
        }
    }
}
