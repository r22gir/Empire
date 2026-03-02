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
    
    // Fee configuration (3% standard)
    uint256 public constant TRANSACTION_FEE_BPS = 300; // 3% in basis points
    uint256 public constant BPS_DENOMINATOR = 10000;
    
    // Tax reserve percentage (configurable per jurisdiction)
    uint256 public taxReserveBps = 2500; // 25% of fees reserved for taxes
    
    // Treasury addresses
    address public treasuryWallet;
    address public taxReserveWallet;
    
    // Product tiers
    enum ProductTier { BASIC_BRAIN, PORTABLE_UNIT, WEB_SAAS, MOBILE_PREMIUM, FOUNDER_EDITION }
    
    // License types
    enum LicenseType { PERPETUAL, SUBSCRIPTION }
    
    // License data
    struct License {
        ProductTier tier;
        LicenseType licenseType;
        uint256 purchaseDate;
        uint256 expirationDate; // 0 for perpetual
        bool isActive;
        string hardwareId; // For hardware-bound licenses
    }
    
    // Pricing in USD (will be converted at purchase time)
    mapping(ProductTier => uint256) public tierPricesUSD;
    mapping(uint256 => License) public licenses;
    
    // Events
    event LicensePurchased(address indexed buyer, uint256 indexed tokenId, ProductTier tier, uint256 price);
    event LicenseRenewed(uint256 indexed tokenId, uint256 newExpiration);
    event LicenseActivated(uint256 indexed tokenId, string hardwareId);
    event FeeDistributed(uint256 toTreasury, uint256 toTaxReserve);
    
    constructor(
        address _treasuryWallet,
        address _taxReserveWallet
    ) ERC721("EmpireBox License", "EMPIRE") Ownable(msg.sender) {
        treasuryWallet = _treasuryWallet;
        taxReserveWallet = _taxReserveWallet;
        
        // Set default prices (in USD cents)
        tierPricesUSD[ProductTier.BASIC_BRAIN] = 100000;      // $1000
        tierPricesUSD[ProductTier.PORTABLE_UNIT] = 50000;     // $500
        tierPricesUSD[ProductTier.WEB_SAAS] = 4900;           // $49/mo
        tierPricesUSD[ProductTier.MOBILE_PREMIUM] = 999;      // $9.99/mo
        tierPricesUSD[ProductTier.FOUNDER_EDITION] = 500000;  // $5000
    }
    
    /**
     * @notice Purchase a license NFT
     * @param tier The product tier to purchase
     * @param licenseType Whether perpetual or subscription
     */
    function purchaseLicense(
        ProductTier tier,
        LicenseType licenseType
    ) external payable nonReentrant returns (uint256) {
        require(msg.value > 0, "Payment required");
        
        _tokenIds++;
        uint256 newTokenId = _tokenIds;
        
        uint256 expiration = 0;
        if (licenseType == LicenseType.SUBSCRIPTION) {
            expiration = block.timestamp + 30 days;
        }
        
        licenses[newTokenId] = License({
            tier: tier,
            licenseType: licenseType,
            purchaseDate: block.timestamp,
            expirationDate: expiration,
            isActive: true,
            hardwareId: ""
        });
        
        _safeMint(msg.sender, newTokenId);
        
        // Distribute fees
        _distributeFees(msg.value);
        
        emit LicensePurchased(msg.sender, newTokenId, tier, msg.value);
        
        return newTokenId;
    }
    
    /**
     * @notice Renew a subscription license
     * @param tokenId The token to renew
     */
    function renewLicense(uint256 tokenId) external payable nonReentrant {
        require(ownerOf(tokenId) == msg.sender, "Not token owner");
        require(licenses[tokenId].licenseType == LicenseType.SUBSCRIPTION, "Not a subscription");
        require(msg.value > 0, "Payment required");
        
        License storage license = licenses[tokenId];
        
        if (license.expirationDate < block.timestamp) {
            license.expirationDate = block.timestamp + 30 days;
        } else {
            license.expirationDate += 30 days;
        }
        
        license.isActive = true;
        
        _distributeFees(msg.value);
        
        emit LicenseRenewed(tokenId, license.expirationDate);
    }
    
    /**
     * @notice Activate license with hardware ID
     * @param tokenId The token to activate
     * @param hardwareId The hardware identifier
     */
    function activateLicense(uint256 tokenId, string calldata hardwareId) external {
        require(ownerOf(tokenId) == msg.sender, "Not token owner");
        require(bytes(licenses[tokenId].hardwareId).length == 0, "Already activated");
        
        licenses[tokenId].hardwareId = hardwareId;
        
        emit LicenseActivated(tokenId, hardwareId);
    }
    
    /**
     * @notice Check if a license is valid
     * @param tokenId The token to check
     */
    function isLicenseValid(uint256 tokenId) external view returns (bool) {
        if (!licenses[tokenId].isActive) return false;
        
        if (licenses[tokenId].licenseType == LicenseType.SUBSCRIPTION) {
            return licenses[tokenId].expirationDate >= block.timestamp;
        }
        
        return true;
    }
    
    /**
     * @notice Distribute fees between treasury and tax reserve
     */
    function _distributeFees(uint256 amount) internal {
        uint256 taxReserve = (amount * taxReserveBps) / BPS_DENOMINATOR;
        uint256 toTreasury = amount - taxReserve;
        
        (bool successTreasury, ) = treasuryWallet.call{value: toTreasury}("");
        require(successTreasury, "Treasury transfer failed");
        
        (bool successTax, ) = taxReserveWallet.call{value: taxReserve}("");
        require(successTax, "Tax reserve transfer failed");
        
        emit FeeDistributed(toTreasury, taxReserve);
    }
    
    // Admin functions
    function setTierPrice(ProductTier tier, uint256 priceUSD) external onlyOwner {
        tierPricesUSD[tier] = priceUSD;
    }
    
    function setTaxReserveBps(uint256 _taxReserveBps) external onlyOwner {
        require(_taxReserveBps <= 5000, "Max 50%");
        taxReserveBps = _taxReserveBps;
    }
    
    function setTreasuryWallet(address _wallet) external onlyOwner {
        treasuryWallet = _wallet;
    }
    
    function setTaxReserveWallet(address _wallet) external onlyOwner {
        taxReserveWallet = _wallet;
    }
    
    // Required overrides for ERC721URIStorage
    function tokenURI(uint256 tokenId) public view override(ERC721, ERC721URIStorage) returns (string memory) {
        return super.tokenURI(tokenId);
    }
    
    function supportsInterface(bytes4 interfaceId) public view override(ERC721, ERC721URIStorage) returns (bool) {
        return super.supportsInterface(interfaceId);
    }
}
