// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title PlainToken
/// @notice Benchmark baseline ONLY. Line-for-line the same ERC20-style token as
///         ComplianceToken, minus the two registry compliance checks, so that
///         the gas difference between the two isolates the cost of the
///         compliance gate itself. Not used by the enforcement demo.
contract PlainToken {
    string public name;
    string public symbol;
    uint8 public constant decimals = 18;
    uint256 public totalSupply;

    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    constructor(string memory _name, string memory _symbol, uint256 _initialSupply, address _initialHolder) {
        name = _name;
        symbol = _symbol;
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
        require(currentAllowance >= amount, "PlainToken: transfer amount exceeds allowance");
        allowance[from][msg.sender] = currentAllowance - amount;
        _transfer(from, to, amount);
        return true;
    }

    function _transfer(address from, address to, uint256 amount) internal {
        require(balanceOf[from] >= amount, "PlainToken: transfer amount exceeds balance");
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        emit Transfer(from, to, amount);
    }
}
