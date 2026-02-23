/// Product data model representing a product to be listed
class Product {
  final String id;
  final String title;
  final double price;
  final String description;
  final String category;
  final String condition;
  final String location;
  final List<String> photoUrls;
  final DateTime createdAt;
  final DateTime? updatedAt;
  final Map<String, dynamic>? metadata;

  Product({
    required this.id,
    required this.title,
    required this.price,
    required this.description,
    required this.category,
    required this.condition,
    required this.location,
    required this.photoUrls,
    required this.createdAt,
    this.updatedAt,
    this.metadata,
  });

  factory Product.fromJson(Map<String, dynamic> json) {
    return Product(
      id: json['id'] as String,
      title: json['title'] as String,
      price: (json['price'] as num).toDouble(),
      description: json['description'] as String,
      category: json['category'] as String,
      condition: json['condition'] as String,
      location: json['location'] as String,
      photoUrls: (json['photoUrls'] as List<dynamic>)
          .map((e) => e as String)
          .toList(),
      createdAt: DateTime.parse(json['createdAt'] as String),
      updatedAt: json['updatedAt'] != null
          ? DateTime.parse(json['updatedAt'] as String)
          : null,
      metadata: json['metadata'] as Map<String, dynamic>?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'price': price,
      'description': description,
      'category': category,
      'condition': condition,
      'location': location,
      'photoUrls': photoUrls,
      'createdAt': createdAt.toIso8601String(),
      'updatedAt': updatedAt?.toIso8601String(),
      'metadata': metadata,
    };
  }

  Product copyWith({
    String? id,
    String? title,
    double? price,
    String? description,
    String? category,
    String? condition,
    String? location,
    List<String>? photoUrls,
    DateTime? createdAt,
    DateTime? updatedAt,
    Map<String, dynamic>? metadata,
  }) {
    return Product(
      id: id ?? this.id,
      title: title ?? this.title,
      price: price ?? this.price,
      description: description ?? this.description,
      category: category ?? this.category,
      condition: condition ?? this.condition,
      location: location ?? this.location,
      photoUrls: photoUrls ?? this.photoUrls,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      metadata: metadata ?? this.metadata,
    );
  }
}

/// Product categories
class ProductCategory {
  static const String electronics = 'Electronics';
  static const String clothing = 'Clothing & Accessories';
  static const String home = 'Home & Garden';
  static const String sports = 'Sports & Outdoors';
  static const String toys = 'Toys & Games';
  static const String books = 'Books & Media';
  static const String automotive = 'Automotive';
  static const String other = 'Other';

  static List<String> get all => [
        electronics,
        clothing,
        home,
        sports,
        toys,
        books,
        automotive,
        other,
      ];
}

/// Product condition options
class ProductCondition {
  static const String newItem = 'New';
  static const String likeNew = 'Like New';
  static const String good = 'Good';
  static const String fair = 'Fair';
  static const String poor = 'Poor';

  static List<String> get all => [
        newItem,
        likeNew,
        good,
        fair,
        poor,
      ];
}
