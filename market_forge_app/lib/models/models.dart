class User {
  final int id;
  final String email;
  final DateTime createdAt;

  User({
    required this.id,
    required this.email,
    required this.createdAt,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'],
      email: json['email'],
      createdAt: DateTime.parse(json['created_at']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'email': email,
      'created_at': createdAt.toIso8601String(),
    };
  }
}

class Listing {
  final int? id;
  final int? userId;
  final String title;
  final String description;
  final double price;
  final String? photoUrl;
  final bool postedEbay;
  final bool postedFacebook;
  final bool postedPoshmark;
  final bool postedMercari;
  final bool postedCraigslist;
  final DateTime? createdAt;

  Listing({
    this.id,
    this.userId,
    required this.title,
    required this.description,
    required this.price,
    this.photoUrl,
    this.postedEbay = false,
    this.postedFacebook = false,
    this.postedPoshmark = false,
    this.postedMercari = false,
    this.postedCraigslist = false,
    this.createdAt,
  });

  factory Listing.fromJson(Map<String, dynamic> json) {
    return Listing(
      id: json['id'],
      userId: json['user_id'],
      title: json['title'],
      description: json['description'],
      price: json['price'].toDouble(),
      photoUrl: json['photo_url'],
      postedEbay: json['posted_ebay'] ?? false,
      postedFacebook: json['posted_facebook'] ?? false,
      postedPoshmark: json['posted_poshmark'] ?? false,
      postedMercari: json['posted_mercari'] ?? false,
      postedCraigslist: json['posted_craigslist'] ?? false,
      createdAt: json['created_at'] != null 
          ? DateTime.parse(json['created_at']) 
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'user_id': userId,
      'title': title,
      'description': description,
      'price': price,
      'photo_url': photoUrl,
      'posted_ebay': postedEbay,
      'posted_facebook': postedFacebook,
      'posted_poshmark': postedPoshmark,
      'posted_mercari': postedMercari,
      'posted_craigslist': postedCraigslist,
      'created_at': createdAt?.toIso8601String(),
    };
  }
}

class Sale {
  final int id;
  final int userId;
  final int listingId;
  final String platform;
  final double salePrice;
  final double commission;
  final bool commissionPaid;
  final DateTime createdAt;

  Sale({
    required this.id,
    required this.userId,
    required this.listingId,
    required this.platform,
    required this.salePrice,
    required this.commission,
    required this.commissionPaid,
    required this.createdAt,
  });

  factory Sale.fromJson(Map<String, dynamic> json) {
    return Sale(
      id: json['id'],
      userId: json['user_id'],
      listingId: json['listing_id'],
      platform: json['platform'],
      salePrice: json['sale_price'].toDouble(),
      commission: json['commission'].toDouble(),
      commissionPaid: json['commission_paid'] ?? false,
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}
