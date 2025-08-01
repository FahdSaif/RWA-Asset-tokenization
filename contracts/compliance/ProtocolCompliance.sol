// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title ProtocolCompliance
 * @dev Example of protocol-level compliance implementation
 */
contract ProtocolCompliance {
    // Compliance administrator
    address public admin;
    
    // Protocol-wide compliance settings
    bool public complianceActive = true;
    
    // Protocol participants registry
    mapping(address => bool) public verifiedParticipants;
    
    // Protocol-wide transfer limits
    uint256 public dailyTransferLimit;
    uint256 public singleTransferLimit;
    
    // Transfer tracking
    mapping(address => mapping(uint256 => uint256)) public dailyTransfers; // user => day => amount
    
    // Events
    event ParticipantVerified(address indexed participant);
    event ComplianceStatusChanged(bool active);
    event TransferLimitsUpdated(uint256 dailyLimit, uint256 singleLimit);
    
    constructor(uint256 _dailyTransferLimit, uint256 _singleTransferLimit) {
        admin = msg.sender;
        dailyTransferLimit = _dailyTransferLimit;
        singleTransferLimit = _singleTransferLimit;
    }
    
    /**
     * @notice Check if a transfer complies with protocol rules
     * @param from Sender address
     * @param to Recipient address
     * @param amount Transfer amount
     * @return Whether the transfer is compliant
     */
    function checkTransferCompliance(
        address from, 
        address to, 
        uint256 amount
    ) public view returns (bool) {
        // Check if compliance is active
        if (!complianceActive) {
            return true; // Skip checks if compliance is disabled
        }
        
        // Check if participants are verified
        if (!verifiedParticipants[from] || !verifiedParticipants[to]) {
            return false;
        }
        
        // Check single transfer limit
        if (amount > singleTransferLimit) {
            return false;
        }
        
        // Check daily transfer limit
        uint256 today = block.timestamp / 1 days;
        if (dailyTransfers[from][today] + amount > dailyTransferLimit) {
            return false;
        }
        
        return true;
    }
    
    /**
     * @notice Record a transfer for daily limit tracking
     * @param user User address
     * @param amount Transfer amount
     */
    function recordTransfer(address user, uint256 amount) external {
        // In production, this would be restricted to protocol contracts
        uint256 today = block.timestamp / 1 days;
        dailyTransfers[user][today] += amount;
    }
    
    /**
     * @notice Verify a participant
     * @param participant Participant address
     */
    function verifyParticipant(address participant) external {
        require(msg.sender == admin, "Only admin can verify participants");
        verifiedParticipants[participant] = true;
        emit ParticipantVerified(participant);
    }
    
    /**
     * @notice Set compliance status
     * @param active Whether compliance is active
     */
    function setComplianceActive(bool active) external {
        require(msg.sender == admin, "Only admin can change compliance status");
        complianceActive = active;
        emit ComplianceStatusChanged(active);
    }
    
    /**
     * @notice Update transfer limits
     * @param _dailyLimit New daily transfer limit
     * @param _singleLimit New single transfer limit
     */
    function updateTransferLimits(uint256 _dailyLimit, uint256 _singleLimit) external {
        require(msg.sender == admin, "Only admin can update limits");
        dailyTransferLimit = _dailyLimit;
        singleTransferLimit = _singleLimit;
        emit TransferLimitsUpdated(_dailyLimit, _singleLimit);
    }
}
