// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@chainlink/contracts/src/v0.8/ChainlinkClient.sol";
import "@chainlink/contracts/src/v0.8/shared/access/ConfirmedOwner.sol";

/**
 * @title RWAOracle
 * @dev Contract that fetches real-world asset data using Chainlink oracles
 */
contract RWAOracle is ChainlinkClient, ConfirmedOwner {
    using Chainlink for Chainlink.Request;
    
    // Oracle response data
    uint256 public assetValue;
    uint256 public lastUpdateTimestamp;
    
    // Chainlink variables
    bytes32 private jobId;
    uint256 private fee;
    
    event AssetValueUpdated(uint256 indexed assetId, uint256 value);
    
    constructor() ConfirmedOwner(msg.sender) {
        setChainlinkToken(0x779877A7B0D9E8603169DdbD7836e478b4624789); // Sepolia LINK
        setChainlinkOracle(0x6090149792dAAeE9D1D568c9f9a6F6B46AA29eFD); // Sepolia Oracle
        jobId = "ca98366cc7314957b8c012c72f05aeeb";
        fee = (1 * LINK_DIVISIBILITY) / 10; // 0.1 LINK
    }
    
    /**
     * @notice Requests asset valuation data from off-chain source
     * @param assetId The identifier of the real-world asset
     */
    function requestAssetValue(uint256 assetId) public {
        Chainlink.Request memory req = buildChainlinkRequest(
            jobId,
            address(this),
            this.fulfill.selector
        );
        
        // Set the URL to fetch data from an API that provides RWA valuations
        req.add("get", "https://api.example.com/assets/valuation");
        req.add("path", "assets.0.value"); // JSON path
        req.addUint("assetId", assetId);
        
        sendChainlinkRequest(req, fee);
    }
    
    /**
     * @notice Callback function for Chainlink oracle response
     */
    function fulfill(bytes32 _requestId, uint256 _assetValue) public recordChainlinkFulfillment(_requestId) {
        assetValue = _assetValue;
        lastUpdateTimestamp = block.timestamp;
        emit AssetValueUpdated(assetValue, block.timestamp);
    }
}
