import 'package:flutter/foundation.dart';
import 'package:market_forge_app/models/user.dart';
import 'package:market_forge_app/services/storage_service.dart';

/// Provider for managing user and authentication state
class UserProvider extends ChangeNotifier {
  final StorageService _storageService = StorageService();
  
  User? _currentUser;
  bool _isAuthenticated = false;
  bool _isLoading = false;

  User? get currentUser => _currentUser;
  bool get isAuthenticated => _isAuthenticated;
  bool get isLoading => _isLoading;

  /// Initialize user state
  Future<void> initialize() async {
    _isLoading = true;
    notifyListeners();

    try {
      // TODO: Load user from secure storage or check authentication
      // For now, create a mock user
      await _loadMockUser();
    } catch (e) {
      print('Error initializing user: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Load mock user for development
  Future<void> _loadMockUser() async {
    await Future.delayed(const Duration(milliseconds: 500));
    
    _currentUser = User(
      id: 'user_123',
      email: 'demo@marketforge.com',
      name: 'Demo User',
      subscriptionTier: SubscriptionTier.pro,
      createdAt: DateTime.now().subtract(const Duration(days: 30)),
      lastLoginAt: DateTime.now(),
      preferences: {
        'notifications': true,
        'autoLocation': true,
        'defaultCategory': 'Electronics',
      },
    );
    _isAuthenticated = true;
  }

  /// Sign in user
  Future<bool> signIn(String email, String password) async {
    _isLoading = true;
    notifyListeners();

    try {
      // TODO: Implement actual authentication
      await Future.delayed(const Duration(seconds: 2));
      
      await _loadMockUser();
      return true;
    } catch (e) {
      print('Error signing in: $e');
      return false;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Sign out user
  Future<void> signOut() async {
    _isLoading = true;
    notifyListeners();

    try {
      // TODO: Implement actual sign out
      await Future.delayed(const Duration(milliseconds: 500));
      
      _currentUser = null;
      _isAuthenticated = false;
      
      // Clear storage
      await _storageService.clearAll();
    } catch (e) {
      print('Error signing out: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Update user profile
  Future<void> updateProfile({
    String? name,
    String? photoUrl,
    Map<String, dynamic>? preferences,
  }) async {
    if (_currentUser == null) return;

    try {
      _currentUser = _currentUser!.copyWith(
        name: name,
        photoUrl: photoUrl,
        preferences: preferences,
      );
      
      // TODO: Save to backend
      notifyListeners();
    } catch (e) {
      print('Error updating profile: $e');
      rethrow;
    }
  }

  /// Update subscription tier
  Future<void> updateSubscription(SubscriptionTier tier) async {
    if (_currentUser == null) return;

    try {
      _currentUser = _currentUser!.copyWith(
        subscriptionTier: tier,
      );
      
      // TODO: Process payment and update backend
      notifyListeners();
    } catch (e) {
      print('Error updating subscription: $e');
      rethrow;
    }
  }

  /// Save user preference
  Future<void> savePreference(String key, dynamic value) async {
    try {
      await _storageService.savePreference(key, value);
      
      if (_currentUser != null) {
        final prefs = Map<String, dynamic>.from(_currentUser!.preferences ?? {});
        prefs[key] = value;
        _currentUser = _currentUser!.copyWith(preferences: prefs);
        notifyListeners();
      }
    } catch (e) {
      print('Error saving preference: $e');
      rethrow;
    }
  }

  /// Get user preference
  dynamic getPreference(String key, {dynamic defaultValue}) {
    return _currentUser?.preferences?[key] ?? defaultValue;
  }

  /// Check if user can list on multiple marketplaces
  bool canListOnMarketplace(int marketplaceCount) {
    if (_currentUser == null) return false;
    
    final maxMarketplaces = _currentUser!.subscriptionTier.maxMarketplaces;
    return maxMarketplaces == -1 || marketplaceCount <= maxMarketplaces;
  }

  /// Get remaining listings for the month
  int get remainingListings {
    if (_currentUser == null) return 0;
    
    final maxListings = _currentUser!.subscriptionTier.maxListingsPerMonth;
    if (maxListings == -1) return -1; // Unlimited
    
    // TODO: Track actual usage
    return maxListings;
  }
}
