/// User subscription tier
enum SubscriptionTier {
  free,
  basic,
  pro,
  enterprise,
}

extension SubscriptionTierExtension on SubscriptionTier {
  String get displayName {
    switch (this) {
      case SubscriptionTier.free:
        return 'Free';
      case SubscriptionTier.basic:
        return 'Basic';
      case SubscriptionTier.pro:
        return 'Pro';
      case SubscriptionTier.enterprise:
        return 'Enterprise';
    }
  }

  int get maxListingsPerMonth {
    switch (this) {
      case SubscriptionTier.free:
        return 10;
      case SubscriptionTier.basic:
        return 50;
      case SubscriptionTier.pro:
        return 200;
      case SubscriptionTier.enterprise:
        return -1; // Unlimited
    }
  }

  int get maxMarketplaces {
    switch (this) {
      case SubscriptionTier.free:
        return 1;
      case SubscriptionTier.basic:
        return 3;
      case SubscriptionTier.pro:
        return 5;
      case SubscriptionTier.enterprise:
        return 6;
    }
  }
}

/// User model
class User {
  final String id;
  final String email;
  final String? name;
  final String? photoUrl;
  final SubscriptionTier subscriptionTier;
  final DateTime createdAt;
  final DateTime? lastLoginAt;
  final Map<String, dynamic>? preferences;

  User({
    required this.id,
    required this.email,
    this.name,
    this.photoUrl,
    required this.subscriptionTier,
    required this.createdAt,
    this.lastLoginAt,
    this.preferences,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'] as String,
      email: json['email'] as String,
      name: json['name'] as String?,
      photoUrl: json['photoUrl'] as String?,
      subscriptionTier: SubscriptionTier.values.firstWhere(
        (e) => e.toString() == json['subscriptionTier'],
        orElse: () => SubscriptionTier.free,
      ),
      createdAt: DateTime.parse(json['createdAt'] as String),
      lastLoginAt: json['lastLoginAt'] != null
          ? DateTime.parse(json['lastLoginAt'] as String)
          : null,
      preferences: json['preferences'] as Map<String, dynamic>?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'email': email,
      'name': name,
      'photoUrl': photoUrl,
      'subscriptionTier': subscriptionTier.toString(),
      'createdAt': createdAt.toIso8601String(),
      'lastLoginAt': lastLoginAt?.toIso8601String(),
      'preferences': preferences,
    };
  }

  User copyWith({
    String? id,
    String? email,
    String? name,
    String? photoUrl,
    SubscriptionTier? subscriptionTier,
    DateTime? createdAt,
    DateTime? lastLoginAt,
    Map<String, dynamic>? preferences,
  }) {
    return User(
      id: id ?? this.id,
      email: email ?? this.email,
      name: name ?? this.name,
      photoUrl: photoUrl ?? this.photoUrl,
      subscriptionTier: subscriptionTier ?? this.subscriptionTier,
      createdAt: createdAt ?? this.createdAt,
      lastLoginAt: lastLoginAt ?? this.lastLoginAt,
      preferences: preferences ?? this.preferences,
    );
  }
}
