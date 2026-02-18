import 'package:market_forge_app/models/product.dart';
import 'package:market_forge_app/models/listing.dart';
import 'package:market_forge_app/models/marketplace.dart';
import 'package:market_forge_app/services/marketplace_service.dart';

/// Mercari marketplace service (stub implementation)
class MercariService extends BaseMarketplaceService {
  @override
  Marketplace get marketplace => Marketplace.mercari;

  @override
  String get name => 'Mercari';

  @override
  bool get isImplemented => false;

  @override
  Future<bool> connect() async {
    throw UnimplementedError('Mercari integration coming soon');
  }

  @override
  Future<bool> disconnect() async {
    throw UnimplementedError('Mercari integration coming soon');
  }

  @override
  Future<ListingResult> postListing(Product product) async {
    return ListingResult(
      success: false,
      errorMessage: 'Mercari integration coming soon',
    );
  }

  @override
  Future<ListingStatus> checkStatus(String listingId) async {
    throw UnimplementedError('Mercari integration coming soon');
  }

  @override
  Future<bool> deleteListing(String listingId) async {
    throw UnimplementedError('Mercari integration coming soon');
  }

  @override
  Future<bool> updateListing(String listingId, Product product) async {
    throw UnimplementedError('Mercari integration coming soon');
  }
}
