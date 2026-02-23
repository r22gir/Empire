import 'package:market_forge_app/services/api_service.dart';
import 'package:market_forge_app/config/app_config.dart';

/// AI service for interacting with EmpireBox AI agents
class AiService {
  final ApiService _apiService;

  AiService({ApiService? apiService})
      : _apiService = apiService ?? ApiService();

  /// Generate title suggestions based on photos and category
  Future<List<String>> generateTitleSuggestions({
    required List<String> photoUrls,
    String? category,
  }) async {
    if (!AppConfig.enableAiTitleSuggestions) {
      return [];
    }

    try {
      final response = await _apiService.post(
        '${AppConfig.aiServiceEndpoint}/generate-title',
        {
          'photoUrls': photoUrls,
          'category': category,
        },
      );

      return (response['suggestions'] as List<dynamic>)
          .map((e) => e as String)
          .toList();
    } catch (e) {
      print('Error generating title suggestions: $e');
      return [];
    }
  }

  /// Enhance product description using AI
  Future<String?> enhanceDescription({
    required String originalDescription,
    required String title,
    required String category,
  }) async {
    if (!AppConfig.enableAiDescriptionEnhancement) {
      return null;
    }

    try {
      final response = await _apiService.post(
        '${AppConfig.aiServiceEndpoint}/enhance-description',
        {
          'description': originalDescription,
          'title': title,
          'category': category,
        },
      );

      return response['enhancedDescription'] as String?;
    } catch (e) {
      print('Error enhancing description: $e');
      return null;
    }
  }

  /// Detect category from photos and title
  Future<String?> detectCategory({
    required List<String> photoUrls,
    String? title,
  }) async {
    if (!AppConfig.enableAiCategoryDetection) {
      return null;
    }

    try {
      final response = await _apiService.post(
        '${AppConfig.aiServiceEndpoint}/detect-category',
        {
          'photoUrls': photoUrls,
          'title': title,
        },
      );

      return response['category'] as String?;
    } catch (e) {
      print('Error detecting category: $e');
      return null;
    }
  }

  /// Suggest price based on similar listings
  Future<double?> suggestPrice({
    required String title,
    required String category,
    required String condition,
  }) async {
    if (!AppConfig.enableAiPriceSuggestions) {
      return null;
    }

    try {
      final response = await _apiService.post(
        '${AppConfig.aiServiceEndpoint}/suggest-price',
        {
          'title': title,
          'category': category,
          'condition': condition,
        },
      );

      return (response['suggestedPrice'] as num?)?.toDouble();
    } catch (e) {
      print('Error suggesting price: $e');
      return null;
    }
  }

  /// Analyze photos for quality and suggestions
  Future<Map<String, dynamic>> analyzePhotos({
    required List<String> photoUrls,
  }) async {
    try {
      final response = await _apiService.post(
        '${AppConfig.aiServiceEndpoint}/analyze-photos',
        {
          'photoUrls': photoUrls,
        },
      );

      return response;
    } catch (e) {
      print('Error analyzing photos: $e');
      return {
        'quality': 'unknown',
        'suggestions': [],
      };
    }
  }
}
