/// Marketplace enum representing supported marketplaces
enum Marketplace {
  facebookMarketplace,
  ebay,
  craigslist,
  amazon,
  etsy,
  mercari,
}

/// Extension to provide marketplace information
extension MarketplaceExtension on Marketplace {
  String get displayName {
    switch (this) {
      case Marketplace.facebookMarketplace:
        return 'Facebook Marketplace';
      case Marketplace.ebay:
        return 'eBay';
      case Marketplace.craigslist:
        return 'Craigslist';
      case Marketplace.amazon:
        return 'Amazon';
      case Marketplace.etsy:
        return 'Etsy';
      case Marketplace.mercari:
        return 'Mercari';
    }
  }

  String get iconName {
    switch (this) {
      case Marketplace.facebookMarketplace:
        return 'facebook';
      case Marketplace.ebay:
        return 'ebay';
      case Marketplace.craigslist:
        return 'craigslist';
      case Marketplace.amazon:
        return 'amazon';
      case Marketplace.etsy:
        return 'etsy';
      case Marketplace.mercari:
        return 'mercari';
    }
  }

  bool get isImplemented {
    switch (this) {
      case Marketplace.facebookMarketplace:
        return true;
      case Marketplace.ebay:
      case Marketplace.craigslist:
      case Marketplace.amazon:
      case Marketplace.etsy:
      case Marketplace.mercari:
        return false;
    }
  }

  String get description {
    switch (this) {
      case Marketplace.facebookMarketplace:
        return 'Post to Facebook Marketplace with ease';
      case Marketplace.ebay:
        return 'List items on eBay auction and buy-it-now';
      case Marketplace.craigslist:
        return 'Post local classified ads on Craigslist';
      case Marketplace.amazon:
        return 'Sell products on Amazon marketplace';
      case Marketplace.etsy:
        return 'List handmade and vintage items on Etsy';
      case Marketplace.mercari:
        return 'Quick selling on Mercari mobile marketplace';
    }
  }
}

/// Marketplace configuration data
class MarketplaceConfig {
  final Marketplace marketplace;
  final bool isConnected;
  final String? apiKey;
  final String? accessToken;
  final DateTime? connectedAt;
  final Map<String, dynamic>? settings;

  MarketplaceConfig({
    required this.marketplace,
    this.isConnected = false,
    this.apiKey,
    this.accessToken,
    this.connectedAt,
    this.settings,
  });

  factory MarketplaceConfig.fromJson(Map<String, dynamic> json) {
    return MarketplaceConfig(
      marketplace: Marketplace.values.firstWhere(
        (e) => e.toString() == json['marketplace'],
      ),
      isConnected: json['isConnected'] as bool? ?? false,
      apiKey: json['apiKey'] as String?,
      accessToken: json['accessToken'] as String?,
      connectedAt: json['connectedAt'] != null
          ? DateTime.parse(json['connectedAt'] as String)
          : null,
      settings: json['settings'] as Map<String, dynamic>?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'marketplace': marketplace.toString(),
      'isConnected': isConnected,
      'apiKey': apiKey,
      'accessToken': accessToken,
      'connectedAt': connectedAt?.toIso8601String(),
      'settings': settings,
    };
  }

  MarketplaceConfig copyWith({
    Marketplace? marketplace,
    bool? isConnected,
    String? apiKey,
    String? accessToken,
    DateTime? connectedAt,
    Map<String, dynamic>? settings,
  }) {
    return MarketplaceConfig(
      marketplace: marketplace ?? this.marketplace,
      isConnected: isConnected ?? this.isConnected,
      apiKey: apiKey ?? this.apiKey,
      accessToken: accessToken ?? this.accessToken,
      connectedAt: connectedAt ?? this.connectedAt,
      settings: settings ?? this.settings,
    );
  }
}
