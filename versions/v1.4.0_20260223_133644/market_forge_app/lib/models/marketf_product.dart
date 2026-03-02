class MarketFProduct {
  final String id;
  final String sellerId;
  final String title;
  final String description;
  final String categoryId;
  final String condition;
  final double price;
  final double? shippingPrice;
  final bool offersEnabled;
  final double? minimumOffer;
  final List<String> images;
  final int packageWeightOz;
  final int packageLengthIn;
  final int packageWidthIn;
  final int packageHeightIn;
  final String shipsFromZip;
  final String status;
  final int quantity;
  final int views;
  final int favorites;
  final DateTime createdAt;
  final DateTime updatedAt;

  MarketFProduct({
    required this.id,
    required this.sellerId,
    required this.title,
    required this.description,
    required this.categoryId,
    required this.condition,
    required this.price,
    this.shippingPrice,
    required this.offersEnabled,
    this.minimumOffer,
    required this.images,
    required this.packageWeightOz,
    required this.packageLengthIn,
    required this.packageWidthIn,
    required this.packageHeightIn,
    required this.shipsFromZip,
    required this.status,
    required this.quantity,
    required this.views,
    required this.favorites,
    required this.createdAt,
    required this.updatedAt,
  });

  factory MarketFProduct.fromJson(Map<String, dynamic> json) {
    return MarketFProduct(
      id: json['id'],
      sellerId: json['seller_id'],
      title: json['title'],
      description: json['description'],
      categoryId: json['category_id'],
      condition: json['condition'],
      price: json['price'].toDouble(),
      shippingPrice: json['shipping_price']?.toDouble(),
      offersEnabled: json['offers_enabled'],
      minimumOffer: json['minimum_offer']?.toDouble(),
      images: List<String>.from(json['images'] ?? []),
      packageWeightOz: json['package_weight_oz'],
      packageLengthIn: json['package_length_in'],
      packageWidthIn: json['package_width_in'],
      packageHeightIn: json['package_height_in'],
      shipsFromZip: json['ships_from_zip'],
      status: json['status'],
      quantity: json['quantity'],
      views: json['views'],
      favorites: json['favorites'],
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'seller_id': sellerId,
      'title': title,
      'description': description,
      'category_id': categoryId,
      'condition': condition,
      'price': price,
      'shipping_price': shippingPrice,
      'offers_enabled': offersEnabled,
      'minimum_offer': minimumOffer,
      'images': images,
      'package_weight_oz': packageWeightOz,
      'package_length_in': packageLengthIn,
      'package_width_in': packageWidthIn,
      'package_height_in': packageHeightIn,
      'ships_from_zip': shipsFromZip,
      'status': status,
      'quantity': quantity,
      'views': views,
      'favorites': favorites,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
    };
  }
}
