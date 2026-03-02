import 'package:market_forge_app/models/product.dart';
import 'package:market_forge_app/models/marketplace.dart';

/// Listing status for a specific marketplace
enum ListingStatus {
  pending,
  posted,
  failed,
  sold,
  deleted,
}

/// Marketplace-specific listing result
class MarketplaceListingStatus {
  final Marketplace marketplace;
  final ListingStatus status;
  final String? listingId;
  final String? errorMessage;
  final String? listingUrl;
  final DateTime timestamp;

  MarketplaceListingStatus({
    required this.marketplace,
    required this.status,
    this.listingId,
    this.errorMessage,
    this.listingUrl,
    required this.timestamp,
  });

  factory MarketplaceListingStatus.fromJson(Map<String, dynamic> json) {
    return MarketplaceListingStatus(
      marketplace: Marketplace.values.firstWhere(
        (e) => e.toString() == json['marketplace'],
      ),
      status: ListingStatus.values.firstWhere(
        (e) => e.toString() == json['status'],
      ),
      listingId: json['listingId'] as String?,
      errorMessage: json['errorMessage'] as String?,
      listingUrl: json['listingUrl'] as String?,
      timestamp: DateTime.parse(json['timestamp'] as String),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'marketplace': marketplace.toString(),
      'status': status.toString(),
      'listingId': listingId,
      'errorMessage': errorMessage,
      'listingUrl': listingUrl,
      'timestamp': timestamp.toIso8601String(),
    };
  }
}

/// Complete listing with product and marketplace statuses
class Listing {
  final String id;
  final Product product;
  final List<Marketplace> targetMarketplaces;
  final List<MarketplaceListingStatus> marketplaceStatuses;
  final DateTime createdAt;
  final DateTime? updatedAt;

  Listing({
    required this.id,
    required this.product,
    required this.targetMarketplaces,
    required this.marketplaceStatuses,
    required this.createdAt,
    this.updatedAt,
  });

  factory Listing.fromJson(Map<String, dynamic> json) {
    return Listing(
      id: json['id'] as String,
      product: Product.fromJson(json['product'] as Map<String, dynamic>),
      targetMarketplaces: (json['targetMarketplaces'] as List<dynamic>)
          .map((e) => Marketplace.values.firstWhere(
                (m) => m.toString() == e,
              ))
          .toList(),
      marketplaceStatuses: (json['marketplaceStatuses'] as List<dynamic>)
          .map((e) =>
              MarketplaceListingStatus.fromJson(e as Map<String, dynamic>))
          .toList(),
      createdAt: DateTime.parse(json['createdAt'] as String),
      updatedAt: json['updatedAt'] != null
          ? DateTime.parse(json['updatedAt'] as String)
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'product': product.toJson(),
      'targetMarketplaces':
          targetMarketplaces.map((m) => m.toString()).toList(),
      'marketplaceStatuses':
          marketplaceStatuses.map((s) => s.toJson()).toList(),
      'createdAt': createdAt.toIso8601String(),
      'updatedAt': updatedAt?.toIso8601String(),
    };
  }

  /// Get overall listing status (worst status among all marketplaces)
  ListingStatus get overallStatus {
    if (marketplaceStatuses.isEmpty) return ListingStatus.pending;
    
    if (marketplaceStatuses.any((s) => s.status == ListingStatus.failed)) {
      return ListingStatus.failed;
    }
    if (marketplaceStatuses.any((s) => s.status == ListingStatus.pending)) {
      return ListingStatus.pending;
    }
    if (marketplaceStatuses.every((s) => s.status == ListingStatus.posted)) {
      return ListingStatus.posted;
    }
    if (marketplaceStatuses.any((s) => s.status == ListingStatus.sold)) {
      return ListingStatus.sold;
    }
    
    return ListingStatus.pending;
  }

  /// Get count of successfully posted marketplaces
  int get postedCount {
    return marketplaceStatuses
        .where((s) => s.status == ListingStatus.posted)
        .length;
  }

  /// Get count of failed marketplaces
  int get failedCount {
    return marketplaceStatuses
        .where((s) => s.status == ListingStatus.failed)
        .length;
  }
}
