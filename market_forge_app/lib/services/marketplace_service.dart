import 'package:market_forge_app/models/product.dart';
import 'package:market_forge_app/models/listing.dart';
import 'package:market_forge_app/models/marketplace.dart';

/// Result of a listing operation
class ListingResult {
  final bool success;
  final String? listingId;
  final String? listingUrl;
  final String? errorMessage;

  ListingResult({
    required this.success,
    this.listingId,
    this.listingUrl,
    this.errorMessage,
  });
}

/// Abstract marketplace service interface
abstract class MarketplaceService {
  /// Marketplace identifier
  Marketplace get marketplace;

  /// Human-readable name
  String get name;

  /// Icon asset path
  String get iconPath;

  /// Whether this marketplace is fully implemented
  bool get isImplemented;

  /// Whether the user has connected their account
  bool get isConnected;

  /// Connect user account to marketplace
  Future<bool> connect();

  /// Disconnect user account from marketplace
  Future<bool> disconnect();

  /// Post a listing to the marketplace
  Future<ListingResult> postListing(Product product);

  /// Check the status of a listing
  Future<ListingStatus> checkStatus(String listingId);

  /// Delete a listing from the marketplace
  Future<bool> deleteListing(String listingId);

  /// Update a listing on the marketplace
  Future<bool> updateListing(String listingId, Product product);

  /// Validate if a product can be listed on this marketplace
  Future<List<String>> validateProduct(Product product);
}

/// Base implementation with common functionality
abstract class BaseMarketplaceService implements MarketplaceService {
  bool _isConnected = false;

  @override
  bool get isConnected => _isConnected;

  @override
  String get iconPath => 'assets/icons/${marketplace.iconName}.png';

  /// Set connection status
  void setConnected(bool connected) {
    _isConnected = connected;
  }

  /// Common validation logic
  @override
  Future<List<String>> validateProduct(Product product) async {
    final errors = <String>[];

    if (product.title.isEmpty) {
      errors.add('Title is required');
    }
    if (product.price <= 0) {
      errors.add('Price must be greater than 0');
    }
    if (product.photoUrls.isEmpty) {
      errors.add('At least one photo is required');
    }
    if (product.description.isEmpty) {
      errors.add('Description is required');
    }

    return errors;
  }
}
