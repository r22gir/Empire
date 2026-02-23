import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:market_forge_app/models/product.dart';
import 'package:market_forge_app/models/listing.dart';

/// Local storage service for managing app data
class StorageService {
  static const String _draftProductsKey = 'draft_products';
  static const String _listingsKey = 'listings';
  static const String _userPreferencesKey = 'user_preferences';
  static const String _marketplaceConfigsKey = 'marketplace_configs';

  /// Save a draft product
  Future<void> saveDraftProduct(Product product) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final drafts = await getDraftProducts();
      
      // Remove existing draft with same ID if any
      drafts.removeWhere((p) => p.id == product.id);
      drafts.add(product);

      final jsonList = drafts.map((p) => p.toJson()).toList();
      await prefs.setString(_draftProductsKey, json.encode(jsonList));
    } catch (e) {
      print('Error saving draft product: $e');
    }
  }

  /// Get all draft products
  Future<List<Product>> getDraftProducts() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final jsonString = prefs.getString(_draftProductsKey);
      
      if (jsonString == null) return [];

      final jsonList = json.decode(jsonString) as List<dynamic>;
      return jsonList
          .map((json) => Product.fromJson(json as Map<String, dynamic>))
          .toList();
    } catch (e) {
      print('Error getting draft products: $e');
      return [];
    }
  }

  /// Delete a draft product
  Future<void> deleteDraftProduct(String productId) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final drafts = await getDraftProducts();
      
      drafts.removeWhere((p) => p.id == productId);

      final jsonList = drafts.map((p) => p.toJson()).toList();
      await prefs.setString(_draftProductsKey, json.encode(jsonList));
    } catch (e) {
      print('Error deleting draft product: $e');
    }
  }

  /// Save a listing
  Future<void> saveListing(Listing listing) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final listings = await getListings();
      
      // Remove existing listing with same ID if any
      listings.removeWhere((l) => l.id == listing.id);
      listings.insert(0, listing); // Add to beginning

      final jsonList = listings.map((l) => l.toJson()).toList();
      await prefs.setString(_listingsKey, json.encode(jsonList));
    } catch (e) {
      print('Error saving listing: $e');
    }
  }

  /// Get all listings
  Future<List<Listing>> getListings() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final jsonString = prefs.getString(_listingsKey);
      
      if (jsonString == null) return [];

      final jsonList = json.decode(jsonString) as List<dynamic>;
      return jsonList
          .map((json) => Listing.fromJson(json as Map<String, dynamic>))
          .toList();
    } catch (e) {
      print('Error getting listings: $e');
      return [];
    }
  }

  /// Delete a listing
  Future<void> deleteListing(String listingId) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final listings = await getListings();
      
      listings.removeWhere((l) => l.id == listingId);

      final jsonList = listings.map((l) => l.toJson()).toList();
      await prefs.setString(_listingsKey, json.encode(jsonList));
    } catch (e) {
      print('Error deleting listing: $e');
    }
  }

  /// Save user preference
  Future<void> savePreference(String key, dynamic value) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final preferences = await getPreferences();
      
      preferences[key] = value;
      await prefs.setString(_userPreferencesKey, json.encode(preferences));
    } catch (e) {
      print('Error saving preference: $e');
    }
  }

  /// Get user preferences
  Future<Map<String, dynamic>> getPreferences() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final jsonString = prefs.getString(_userPreferencesKey);
      
      if (jsonString == null) return {};

      return json.decode(jsonString) as Map<String, dynamic>;
    } catch (e) {
      print('Error getting preferences: $e');
      return {};
    }
  }

  /// Clear all data
  Future<void> clearAll() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.clear();
    } catch (e) {
      print('Error clearing storage: $e');
    }
  }
}
