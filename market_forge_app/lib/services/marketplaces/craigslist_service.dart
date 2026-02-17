import 'package:market_forge_app/models/product.dart';
import 'package:market_forge_app/models/listing.dart';
import 'package:market_forge_app/models/marketplace.dart';
import 'package:market_forge_app/services/marketplace_service.dart';

/// Craigslist service (stub implementation)
class CraigslistService extends BaseMarketplaceService {
  @override
  Marketplace get marketplace => Marketplace.craigslist;

  @override
  String get name => 'Craigslist';

  @override
  bool get isImplemented => false;

  @override
  Future<bool> connect() async {
    throw UnimplementedError('Craigslist integration coming soon');
  }

  @override
  Future<bool> disconnect() async {
    throw UnimplementedError('Craigslist integration coming soon');
  }

  @override
  Future<ListingResult> postListing(Product product) async {
    return ListingResult(
      success: false,
      errorMessage: 'Craigslist integration coming soon',
    );
  }

  @override
  Future<ListingStatus> checkStatus(String listingId) async {
    throw UnimplementedError('Craigslist integration coming soon');
  }

  @override
  Future<bool> deleteListing(String listingId) async {
    throw UnimplementedError('Craigslist integration coming soon');
  }

  @override
  Future<bool> updateListing(String listingId, Product product) async {
    throw UnimplementedError('Craigslist integration coming soon');
  }
}
