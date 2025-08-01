mkdir rwa-tokenization
cd rwa-tokenization
npm init -y
npm install --save-dev hardhat @nomiclabs/hardhat-ethers ethers @nomiclabs/hardhat-waffle ethereum-waffle chai @openzeppelin/contracts
npx hardhat

require("@nomiclabs/hardhat-waffle");

module.exports = {
  solidity: "0.8.20",
  networks: {
    hardhat: {
      mining: {
        auto: true,
        interval: 0
      }
    }
  }
};
