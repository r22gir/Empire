import 'package:flutter/foundation.dart';
import 'package:market_forge_app/models/product.dart';
import 'package:market_forge_app/models/listing.dart';
import 'package:market_forge_app/models/marketplace.dart';
import 'package:market_forge_app/services/storage_service.dart';
import 'package:market_forge_app/services/marketplaces/facebook_marketplace.dart';
import 'package:market_forge_app/services/marketplaces/ebay_service.dart';
import 'package:market_forge_app/services/marketplaces/craigslist_service.dart';
import 'package:market_forge_app/services/marketplaces/amazon_service.dart';
import 'package:market_forge_app/services/marketplaces/etsy_service.dart';
import 'package:market_forge_app/services/marketplaces/mercari_service.dart';
import 'package:market_forge_app/services/marketplace_service.dart';
import 'package:uuid/uuid.dart';

/// Provider for managing listing flow and state
class ListingProvider extends ChangeNotifier {
  final StorageService _storageService = StorageService();
  final Map<Marketplace, MarketplaceService> _services = {};
  
  Product? _currentProduct;
  List<Marketplace> _selectedMarketplaces = [];
  List<Listing> _listings = [];
  bool _isPosting = false;

  ListingProvider() {
    _initializeServices();
  }

  void _initializeServices() {
    _services[Marketplace.facebookMarketplace] = FacebookMarketplaceService();
    _services[Marketplace.ebay] = EbayService();
    _services[Marketplace.craigslist] = CraigslistService();
    _services[Marketplace.amazon] = AmazonService();
    _services[Marketplace.etsy] = EtsyService();
    _services[Marketplace.mercari] = MercariService();
  }

  Product? get currentProduct => _currentProduct;
  List<Marketplace> get selectedMarketplaces => List.unmodifiable(_selectedMarketplaces);
  List<Listing> get listings => List.unmodifiable(_listings);
  bool get isPosting => _isPosting;

  MarketplaceService getService(Marketplace marketplace) {
    return _services[marketplace]!;
  }

  /// Initialize and load listings
  Future<void> initialize() async {
    try {
      final loadedListings = await _storageService.getListings();
      _listings.clear();
      _listings.addAll(loadedListings);
      notifyListeners();
    } catch (e) {
      print('Error initializing listings: $e');
    }
  }

  /// Start a new listing flow
  void startNewListing(Product product) {
    _currentProduct = product;
    _selectedMarketplaces.clear();
    notifyListeners();
  }

  /// Update the current product
  void updateCurrentProduct(Product product) {
    _currentProduct = product;
    notifyListeners();
  }

  /// Toggle marketplace selection
  void toggleMarketplace(Marketplace marketplace) {
    if (_selectedMarketplaces.contains(marketplace)) {
      _selectedMarketplaces.remove(marketplace);
    } else {
      _selectedMarketplaces.add(marketplace);
    }
    notifyListeners();
  }

  /// Set selected marketplaces
  void setSelectedMarketplaces(List<Marketplace> marketplaces) {
    _selectedMarketplaces = List.from(marketplaces);
    notifyListeners();
  }

  /// Post listing to selected marketplaces
  Future<Listing> postListing() async {
    if (_currentProduct == null) {
      throw Exception('No product to post');
    }

    _isPosting = true;
    notifyListeners();

    try {
      final listingId = const Uuid().v4();
      final statuses = <MarketplaceListingStatus>[];

      // Post to each selected marketplace
      for (final marketplace in _selectedMarketplaces) {
        final service = _services[marketplace]!;
        
        if (!service.isImplemented) {
          // Add pending status for unimplemented marketplaces
          statuses.add(MarketplaceListingStatus(
            marketplace: marketplace,
            status: ListingStatus.failed,
            errorMessage: '${service.name} integration coming soon',
            timestamp: DateTime.now(),
          ));
          continue;
        }

        try {
          final result = await service.postListing(_currentProduct!);
          
          statuses.add(MarketplaceListingStatus(
            marketplace: marketplace,
            status: result.success ? ListingStatus.posted : ListingStatus.failed,
            listingId: result.listingId,
            listingUrl: result.listingUrl,
            errorMessage: result.errorMessage,
            timestamp: DateTime.now(),
          ));
        } catch (e) {
          statuses.add(MarketplaceListingStatus(
            marketplace: marketplace,
            status: ListingStatus.failed,
            errorMessage: 'Error: $e',
            timestamp: DateTime.now(),
          ));
        }
      }

      // Create and save listing
      final listing = Listing(
        id: listingId,
        product: _currentProduct!,
        targetMarketplaces: _selectedMarketplaces,
        marketplaceStatuses: statuses,
        createdAt: DateTime.now(),
      );

      await _storageService.saveListing(listing);
      _listings.insert(0, listing);

      // Clear current listing state
      _currentProduct = null;
      _selectedMarketplaces.clear();

      return listing;
    } finally {
      _isPosting = false;
      notifyListeners();
    }
  }

  /// Delete a listing
  Future<void> deleteListing(String listingId) async {
    try {
      await _storageService.deleteListing(listingId);
      _listings.removeWhere((l) => l.id == listingId);
      notifyListeners();
    } catch (e) {
      print('Error deleting listing: $e');
      rethrow;
    }
  }

  /// Cancel current listing flow
  void cancelListing() {
    _currentProduct = null;
    _selectedMarketplaces.clear();
    notifyListeners();
  }

  /// Get listing by ID
  Listing? getListingById(String id) {
    try {
      return _listings.firstWhere((l) => l.id == id);
    } catch (e) {
      return null;
    }
  }

  /// Get total count of successful posts
  int get totalPostedCount {
    return _listings.fold<int>(
      0,
      (sum, listing) => sum + listing.postedCount,
    );
  }

  /// Get total count of failed posts
  int get totalFailedCount {
    return _listings.fold<int>(
      0,
      (sum, listing) => sum + listing.failedCount,
    );
  }
}
