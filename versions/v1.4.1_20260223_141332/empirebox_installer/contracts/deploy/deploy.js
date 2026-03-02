// Hardhat deployment script for EmpireBoxLicense
const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying with account:", deployer.address);

  // Configure wallets - UPDATE THESE
  const treasuryWallet = process.env.TREASURY_WALLET || deployer.address;
  const taxReserveWallet = process.env.TAX_WALLET || deployer.address;

  const EmpireBoxLicense = await hre.ethers.getContractFactory("EmpireBoxLicense");
  const license = await EmpireBoxLicense.deploy(treasuryWallet, taxReserveWallet);
  await license.waitForDeployment();

  const address = await license.getAddress();
  console.log("EmpireBoxLicense deployed to:", address);
  
  // Save deployment info
  const fs = require("fs");
  const deployment = {
    network: hre.network.name,
    address: address,
    treasury: treasuryWallet,
    taxReserve: taxReserveWallet,
    deployer: deployer.address,
    timestamp: new Date().toISOString()
  };
  
  fs.writeFileSync(
    `deployments/${hre.network.name}.json`,
    JSON.stringify(deployment, null, 2)
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
