/// Application configuration including API endpoints and feature flags
class AppConfig {
  // API Configuration
  static const String baseUrl = 'https://api.empirebox.com';
  static const String apiVersion = 'v1';
  
  // Endpoints
  static const String aiServiceEndpoint = '$baseUrl/$apiVersion/ai';
  static const String marketplaceEndpoint = '$baseUrl/$apiVersion/marketplace';
  static const String userEndpoint = '$baseUrl/$apiVersion/user';
  static const String listingsEndpoint = '$baseUrl/$apiVersion/listings';
  
  // Feature Flags
  static const bool enableFacebookMarketplace = true;
  static const bool enableEbay = false;
  static const bool enableCraigslist = false;
  static const bool enableAmazon = false;
  static const bool enableEtsy = false;
  static const bool enableMercari = false;
  
  // AI Features
  static const bool enableAiTitleSuggestions = true;
  static const bool enableAiDescriptionEnhancement = true;
  static const bool enableAiCategoryDetection = true;
  static const bool enableAiPriceSuggestions = true;
  
  // App Settings
  static const int maxPhotosPerListing = 10;
  static const int maxListingTitleLength = 100;
  static const int maxListingDescriptionLength = 5000;
  
  // Timeouts (in seconds)
  static const int apiTimeout = 30;
  static const int uploadTimeout = 60;
  
  // Cache Settings
  static const int cacheDuration = 3600; // 1 hour in seconds
  
  // Debug Settings
  static const bool enableDebugMode = true;
  static const bool enableLogging = true;
}
