// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title ComplianceRegistry
/// @notice On-chain counterpart of the paper's Rule Registry / Asset & Governance
///         layers, scoped down to the single predicate a transfer-restricted
///         token needs at the EVM level: "is this address currently compliant?"
///         Off-chain, the ARCA Python prototype's RuleRegistryModule and
///         GovernanceModule decide *why* an address is or is not allowed
///         (jurisdiction checks, ZKP-verified eligibility, risk/anomaly CRRs);
///         this contract is where that decision becomes an on-chain fact that
///         ComplianceToken can enforce unconditionally.
/// @dev    In a production deployment `owner` would itself be a multisig or a
///         governance contract that only accepts the equivalent of a
///         GovernanceAuthorization (Sec. V-F) as required signatures.
contract ComplianceRegistry {
    address public owner;

    mapping(address => bool) public allowed;
    mapping(address => bool) public flagged;

    event AllowlistUpdated(address indexed account, bool allowedStatus);
    event AddressFlagged(address indexed account, bool flaggedStatus);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    modifier onlyOwner() {
        require(msg.sender == owner, "ComplianceRegistry: caller is not owner");
        _;
    }

    constructor(address _owner) {
        require(_owner != address(0), "ComplianceRegistry: owner is zero address");
        owner = _owner;
    }

    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "ComplianceRegistry: new owner is zero address");
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
    }

    /// @notice Governance-authorized allowlist update (paper Sec. V-E: rule
    ///         updates accepted only from a validated governance decision).
    function setAllowed(address account, bool status) external onlyOwner {
        allowed[account] = status;
        emit AllowlistUpdated(account, status);
    }

    function setAllowedBatch(address[] calldata accounts, bool status) external onlyOwner {
        for (uint256 i = 0; i < accounts.length; i++) {
            allowed[accounts[i]] = status;
            emit AllowlistUpdated(accounts[i], status);
        }
    }

    /// @notice Set by an off-chain anomaly/risk CRR outcome (paper Sec. V-C,
    ///         Behavioural Anomaly Detection Agent) once relayed on-chain by
    ///         governance. Flagged addresses cannot transact even if
    ///         allow-listed, until cleared.
    function setFlagged(address account, bool status) external onlyOwner {
        flagged[account] = status;
        emit AddressFlagged(account, status);
    }

    /// @notice The single predicate ComplianceToken relies on before any
    ///         transfer is permitted.
    function isCompliant(address account) public view returns (bool) {
        return allowed[account] && !flagged[account];
    }
}
