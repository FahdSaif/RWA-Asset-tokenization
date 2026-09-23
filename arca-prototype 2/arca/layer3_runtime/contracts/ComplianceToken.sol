// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./ComplianceRegistry.sol";

/// @title ComplianceToken
/// @notice Minimal, self-contained ERC20-style token instantiating the paper's
///         "compliance-capable token standards that incorporate transfer
///         restriction hooks enabling the Runtime Enforcement Layer to
///         intercept each transaction before execution" (Sec. V-F).
///
///         The key architectural point this contract demonstrates (Sec. VI-B,
///         Threat Class I: Direct Protocol Bypass Attempt) is that the
///         compliance check lives INSIDE `_transfer`, which every public
///         transfer path (`transfer`, `transferFrom`) routes through. There is
///         no "front-end only" check to bypass: a transaction constructed by
///         hand and submitted directly to this contract's `transfer` function
///         hits the exact same `require(registry.isCompliant(...))` as one
///         submitted through an application UI.
///
/// @dev    This is intentionally NOT a production ERC-20: no SafeMath needed
///         (Solidity >=0.8 has checked arithmetic), no OpenZeppelin dependency
///         (kept self-contained for a minimal, auditable reference example).
///         A production deployment should build on an audited base (e.g.
///         OpenZeppelin's ERC20) with this same `_beforeTokenTransfer`-style
///         hook layered on top, and should route registry updates through a
///         real governance/multisig contract rather than a single EOA owner.
contract ComplianceToken {
    string public name;
    string public symbol;
    uint8 public constant decimals = 18;
    uint256 public totalSupply;

    ComplianceRegistry public registry;

    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    constructor(
        string memory _name,
        string memory _symbol,
        uint256 _initialSupply,
        address _registry,
        address _initialHolder
    ) {
        name = _name;
        symbol = _symbol;
        registry = ComplianceRegistry(_registry);
        totalSupply = _initialSupply;
        balanceOf[_initialHolder] = _initialSupply;
        emit Transfer(address(0), _initialHolder, _initialSupply);
    }

    function transfer(address to, uint256 amount) external returns (bool) {
        _transfer(msg.sender, to, amount);
        return true;
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        uint256 currentAllowance = allowance[from][msg.sender];
        require(currentAllowance >= amount, "ComplianceToken: transfer amount exceeds allowance");
        allowance[from][msg.sender] = currentAllowance - amount;
        _transfer(from, to, amount);
        return true;
    }

    /// @dev The non-bypassable compliance gate. Every transfer path above
    ///      routes through here before any balance is mutated.
    ///
    ///      Note: this function deliberately does NOT emit a
    ///      "rejected" event before reverting. On the EVM, a `revert`
    ///      unwinds ALL state changes AND events from the current call —
    ///      an event emitted immediately before a revert is discarded
    ///      along with everything else and is never actually written to a
    ///      block. The structured rejection reason is instead delivered
    ///      via the revert string itself, which every client (including
    ///      arca/layer3_runtime/evm_bridge.py) reads from the failed
    ///      transaction's error message — the on-chain equivalent of the
    ///      Python TransactionValidationModule's `rejection_reasons` list.
    function _transfer(address from, address to, uint256 amount) internal {
        require(registry.isCompliant(from), "ARCA: sender not compliant");
        require(registry.isCompliant(to), "ARCA: receiver not compliant");
        require(balanceOf[from] >= amount, "ComplianceToken: transfer amount exceeds balance");

        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        emit Transfer(from, to, amount);
    }
}
