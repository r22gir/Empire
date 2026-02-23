import 'package:flutter/foundation.dart';
import 'package:market_forge_app/models/product.dart';
import 'package:market_forge_app/services/storage_service.dart';
import 'package:uuid/uuid.dart';

/// Provider for managing product state
class ProductProvider extends ChangeNotifier {
  final StorageService _storageService = StorageService();
  final List<Product> _draftProducts = [];
  
  bool _isLoading = false;

  List<Product> get draftProducts => List.unmodifiable(_draftProducts);
  bool get isLoading => _isLoading;

  /// Initialize and load draft products
  Future<void> initialize() async {
    _isLoading = true;
    notifyListeners();

    try {
      final drafts = await _storageService.getDraftProducts();
      _draftProducts.clear();
      _draftProducts.addAll(drafts);
    } catch (e) {
      print('Error initializing products: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Create a new draft product
  Product createDraft({
    String? title,
    double? price,
    String? description,
    String? category,
    String? condition,
    String? location,
    List<String>? photoUrls,
  }) {
    final product = Product(
      id: const Uuid().v4(),
      title: title ?? '',
      price: price ?? 0.0,
      description: description ?? '',
      category: category ?? ProductCategory.other,
      condition: condition ?? ProductCondition.good,
      location: location ?? '',
      photoUrls: photoUrls ?? [],
      createdAt: DateTime.now(),
    );

    return product;
  }

  /// Save a draft product
  Future<void> saveDraft(Product product) async {
    try {
      await _storageService.saveDraftProduct(product);
      
      // Update local list
      final index = _draftProducts.indexWhere((p) => p.id == product.id);
      if (index >= 0) {
        _draftProducts[index] = product;
      } else {
        _draftProducts.add(product);
      }
      
      notifyListeners();
    } catch (e) {
      print('Error saving draft: $e');
      rethrow;
    }
  }

  /// Delete a draft product
  Future<void> deleteDraft(String productId) async {
    try {
      await _storageService.deleteDraftProduct(productId);
      _draftProducts.removeWhere((p) => p.id == productId);
      notifyListeners();
    } catch (e) {
      print('Error deleting draft: $e');
      rethrow;
    }
  }

  /// Get a specific draft product by ID
  Product? getDraftById(String id) {
    try {
      return _draftProducts.firstWhere((p) => p.id == id);
    } catch (e) {
      return null;
    }
  }

  /// Update a draft product
  Future<void> updateDraft(Product product) async {
    await saveDraft(product);
  }

  /// Clear all drafts
  Future<void> clearAllDrafts() async {
    try {
      for (final product in _draftProducts) {
        await _storageService.deleteDraftProduct(product.id);
      }
      _draftProducts.clear();
      notifyListeners();
    } catch (e) {
      print('Error clearing drafts: $e');
      rethrow;
    }
  }
}
