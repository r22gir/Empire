// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title EmpireBox License NFT
 * @notice License NFT for EmpireBox products with automatic fee distribution
 * @dev Supports multiple product tiers with 3% transaction fee
 */
contract EmpireBoxLicense is ERC721, ERC721URIStorage, Ownable, ReentrancyGuard {
    uint256 private _tokenIds;
    
    // Fee configuration (basis points: 300 = 3%)
    uint256 public constant TRANSACTION_FEE_BPS = 300;
    uint256 public constant BPS_DENOMINATOR = 10000;
    
    // Tax reserve for fiscal compliance (configurable)
    uint256 public taxReserveBps = 0;
    
    // Wallets
    address public treasuryWallet;
    address public taxReserveWallet;
    
    // Product tiers
    enum ProductTier { 
        BASIC_BRAIN,      // $1000+ hardware unit
        PORTABLE_UNIT,    // $500+ software license
        WEB_SAAS,         // $49/mo subscription
        MOBILE_PREMIUM,   // $9.99/mo mobile
        FOUNDER_EDITION   // Special founder access
    }
    
    // License structure
    struct License {
        ProductTier tier;
        uint256 purchasePrice;
        uint256 purchaseDate;
        uint256 expirationDate;
        bool isActive;
        string activationKey;
    }
    
    // Mappings
    mapping(uint256 => License) public licenses;
    mapping(string => uint256) public activationKeyToToken;
    mapping(address => uint256[]) public ownerLicenses;
    mapping(ProductTier => uint256) public tierPrices;
    
    // Events
    event LicensePurchased(uint256 indexed tokenId, address indexed buyer, ProductTier tier, uint256 price, string activationKey);
    event LicenseActivated(uint256 indexed tokenId, address indexed owner);
    event LicenseDeactivated(uint256 indexed tokenId);
    event FeeDistributed(uint256 sellerAmount, uint256 feeAmount, uint256 taxAmount);
    event TierPriceUpdated(ProductTier tier, uint256 newPrice);
    
    constructor(address _treasuryWallet, address _taxReserveWallet) 
        ERC721("EmpireBox License", "EMPIRE") 
        Ownable(msg.sender) 
    {
        treasuryWallet = _treasuryWallet;
        taxReserveWallet = _taxReserveWallet;
        
        tierPrices[ProductTier.BASIC_BRAIN] = 0.5 ether;
        tierPrices[ProductTier.PORTABLE_UNIT] = 0.25 ether;
        tierPrices[ProductTier.WEB_SAAS] = 0.025 ether;
        tierPrices[ProductTier.MOBILE_PREMIUM] = 0.005 ether;
        tierPrices[ProductTier.FOUNDER_EDITION] = 1 ether;
    }
    
    function purchaseLicense(ProductTier tier, address seller) external payable nonReentrant returns (uint256) {
        require(msg.value >= tierPrices[tier], "Insufficient payment");
        require(seller != address(0), "Invalid seller");
        
        uint256 totalFee = (msg.value * TRANSACTION_FEE_BPS) / BPS_DENOMINATOR;
        uint256 taxAmount = (msg.value * taxReserveBps) / BPS_DENOMINATOR;
        uint256 sellerAmount = msg.value - totalFee - taxAmount;
        
        (bool sellerSuccess, ) = payable(seller).call{value: sellerAmount}("");
        require(sellerSuccess, "Seller payment failed");
        
        (bool feeSuccess, ) = payable(treasuryWallet).call{value: totalFee}("");
        require(feeSuccess, "Fee payment failed");
        
        if (taxAmount > 0) {
            (bool taxSuccess, ) = payable(taxReserveWallet).call{value: taxAmount}("");
            require(taxSuccess, "Tax reserve payment failed");
        }
        
        emit FeeDistributed(sellerAmount, totalFee, taxAmount);
        
        _tokenIds++;
        uint256 newTokenId = _tokenIds;
        
        string memory activationKey = _generateActivationKey(newTokenId, msg.sender);
        
        uint256 expiration = 0;
        if (tier == ProductTier.WEB_SAAS || tier == ProductTier.MOBILE_PREMIUM) {
            expiration = block.timestamp + 30 days;
        }
        
        licenses[newTokenId] = License({
            tier: tier,
            purchasePrice: msg.value,
            purchaseDate: block.timestamp,
            expirationDate: expiration,
            isActive: true,
            activationKey: activationKey
        });
        
        activationKeyToToken[activationKey] = newTokenId;
        ownerLicenses[msg.sender].push(newTokenId);
        
        _safeMint(msg.sender, newTokenId);
        
        emit LicensePurchased(newTokenId, msg.sender, tier, msg.value, activationKey);
        return newTokenId;
    }
    
    function isLicenseValid(uint256 tokenId) public view returns (bool) {
        if (_ownerOf(tokenId) == address(0)) return false;
        License memory license = licenses[tokenId];
        if (!license.isActive) return false;
        if (license.expirationDate > 0 && block.timestamp > license.expirationDate) return false;
        return true;
    }
    
    function verifyActivationKey(string memory activationKey) external view returns (bool valid, uint256 tokenId, address owner, ProductTier tier) {
        tokenId = activationKeyToToken[activationKey];
        if (tokenId == 0) return (false, 0, address(0), ProductTier.BASIC_BRAIN);
        valid = isLicenseValid(tokenId);
        owner = ownerOf(tokenId);
        tier = licenses[tokenId].tier;
    }
    
    function renewLicense(uint256 tokenId) external payable nonReentrant {
        require(_ownerOf(tokenId) != address(0), "License does not exist");
        require(ownerOf(tokenId) == msg.sender, "Not license owner");
        
        License storage license = licenses[tokenId];
        require(license.tier == ProductTier.WEB_SAAS || license.tier == ProductTier.MOBILE_PREMIUM, "Only subscriptions can be renewed");
        require(msg.value >= tierPrices[license.tier], "Insufficient payment");
        
        uint256 totalFee = (msg.value * TRANSACTION_FEE_BPS) / BPS_DENOMINATOR;
        (bool feeSuccess, ) = payable(treasuryWallet).call{value: totalFee}("");
        require(feeSuccess, "Fee payment failed");
        
        if (license.expirationDate < block.timestamp) {
            license.expirationDate = block.timestamp + 30 days;
        } else {
            license.expirationDate += 30 days;
        }
        license.isActive = true;
    }
    
    function _generateActivationKey(uint256 tokenId, address buyer) internal view returns (string memory) {
        bytes32 hash = keccak256(abi.encodePacked(tokenId, buyer, block.timestamp, block.prevrandao));
        return string(abi.encodePacked("EMPIRE-", _toHex(uint32(uint256(hash) >> 224)), "-", _toHex(uint32(uint256(hash) >> 192)), "-", _toHex(uint32(uint256(hash) >> 160)), "-", _toHex(uint32(uint256(hash) >> 128))));
    }
    
    function _toHex(uint32 value) internal pure returns (string memory) {
        bytes memory buffer = new bytes(4);
        bytes memory alphabet = "0123456789ABCDEF";
        for (uint256 i = 0; i < 4; i++) { buffer[3 - i] = alphabet[value & 0xf]; value >>= 4; }
        return string(buffer);
    }
    
    // Admin functions
    function setTierPrice(ProductTier tier, uint256 price) external onlyOwner { tierPrices[tier] = price; emit TierPriceUpdated(tier, price); }
    function setTaxReserve(uint256 bps) external onlyOwner { require(bps <= 2000, "Max 20%"); taxReserveBps = bps; }
    function setTreasuryWallet(address wallet) external onlyOwner { require(wallet != address(0), "Invalid"); treasuryWallet = wallet; }
    function setTaxReserveWallet(address wallet) external onlyOwner { require(wallet != address(0), "Invalid"); taxReserveWallet = wallet; }
    function deactivateLicense(uint256 tokenId) external onlyOwner { licenses[tokenId].isActive = false; emit LicenseDeactivated(tokenId); }
    
    // Overrides
    function _burn(uint256 tokenId) internal override(ERC721, ERC721URIStorage) { super._burn(tokenId); }
    function tokenURI(uint256 tokenId) public view override(ERC721, ERC721URIStorage) returns (string memory) { return super.tokenURI(tokenId); }
    function supportsInterface(bytes4 interfaceId) public view override(ERC721, ERC721URIStorage) returns (bool) { return super.supportsInterface(interfaceId); }
    
    function getLicenses(address owner) external view returns (uint256[] memory) { return ownerLicenses[owner]; }
    function getLicenseDetails(uint256 tokenId) external view returns (ProductTier, uint256, uint256, uint256, bool, string memory, bool) {
        License memory l = licenses[tokenId];
        return (l.tier, l.purchasePrice, l.purchaseDate, l.expirationDate, l.isActive, l.activationKey, isLicenseValid(tokenId));
    }
}
