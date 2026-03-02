import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/marketf_product.dart';
import '../models/marketf_order.dart';
import '../models/marketf_review.dart';

class MarketFService {
  final String baseUrl;

  MarketFService({this.baseUrl = 'http://localhost:8000'});

  // Products
  Future<List<MarketFProduct>> getProducts({
    String? category,
    String? condition,
    double? minPrice,
    double? maxPrice,
    String sort = 'newest',
    int page = 1,
    int perPage = 24,
  }) async {
    final queryParams = <String, String>{
      'page': page.toString(),
      'per_page': perPage.toString(),
      'sort': sort,
    };

    if (category != null) queryParams['category'] = category;
    if (condition != null) queryParams['condition'] = condition;
    if (minPrice != null) queryParams['min_price'] = minPrice.toString();
    if (maxPrice != null) queryParams['max_price'] = maxPrice.toString();

    final uri = Uri.parse('$baseUrl/marketplace/products').replace(queryParameters: queryParams);
    final response = await http.get(uri);

    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      final List productsJson = data['products'] ?? [];
      return productsJson.map((json) => MarketFProduct.fromJson(json)).toList();
    } else {
      throw Exception('Failed to load products');
    }
  }

  Future<MarketFProduct> getProduct(String id) async {
    final response = await http.get(Uri.parse('$baseUrl/marketplace/products/$id'));

    if (response.statusCode == 200) {
      return MarketFProduct.fromJson(json.decode(response.body));
    } else {
      throw Exception('Failed to load product');
    }
  }

  Future<MarketFProduct> createProduct(Map<String, dynamic> productData) async {
    final response = await http.post(
      Uri.parse('$baseUrl/marketplace/products'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode(productData),
    );

    if (response.statusCode == 201) {
      return MarketFProduct.fromJson(json.decode(response.body));
    } else {
      throw Exception('Failed to create product');
    }
  }

  // Orders
  Future<List<MarketFOrder>> getOrders({int page = 1, int perPage = 50}) async {
    final uri = Uri.parse('$baseUrl/marketplace/orders').replace(queryParameters: {
      'page': page.toString(),
      'per_page': perPage.toString(),
    });
    final response = await http.get(uri);

    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      final List ordersJson = data['orders'] ?? [];
      return ordersJson.map((json) => MarketFOrder.fromJson(json)).toList();
    } else {
      throw Exception('Failed to load orders');
    }
  }

  Future<MarketFOrder> getOrder(String id) async {
    final response = await http.get(Uri.parse('$baseUrl/marketplace/orders/$id'));

    if (response.statusCode == 200) {
      return MarketFOrder.fromJson(json.decode(response.body));
    } else {
      throw Exception('Failed to load order');
    }
  }

  Future<MarketFOrder> createOrder(Map<String, dynamic> orderData) async {
    final response = await http.post(
      Uri.parse('$baseUrl/marketplace/orders'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode(orderData),
    );

    if (response.statusCode == 201) {
      return MarketFOrder.fromJson(json.decode(response.body));
    } else {
      throw Exception('Failed to create order');
    }
  }

  Future<MarketFOrder> shipOrder(String orderId, String trackingNumber, String carrier) async {
    final response = await http.post(
      Uri.parse('$baseUrl/marketplace/orders/$orderId/ship'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({
        'tracking_number': trackingNumber,
        'carrier': carrier,
      }),
    );

    if (response.statusCode == 200) {
      return MarketFOrder.fromJson(json.decode(response.body));
    } else {
      throw Exception('Failed to ship order');
    }
  }

  // Reviews
  Future<MarketFReview> createReview(String orderId, Map<String, dynamic> reviewData) async {
    final response = await http.post(
      Uri.parse('$baseUrl/marketplace/orders/$orderId/review'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode(reviewData),
    );

    if (response.statusCode == 201) {
      return MarketFReview.fromJson(json.decode(response.body));
    } else {
      throw Exception('Failed to create review');
    }
  }

  Future<List<MarketFReview>> getUserReviews(String userId) async {
    final response = await http.get(Uri.parse('$baseUrl/marketplace/users/$userId/reviews'));

    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      final List reviewsJson = data['reviews'] ?? [];
      return reviewsJson.map((json) => MarketFReview.fromJson(json)).toList();
    } else {
      throw Exception('Failed to load reviews');
    }
  }

  // Seller Orders
  Future<List<MarketFOrder>> getSellerOrders({String? status, int page = 1, int perPage = 50}) async {
    final queryParams = <String, String>{
      'page': page.toString(),
      'per_page': perPage.toString(),
    };
    if (status != null) queryParams['status'] = status;

    final uri = Uri.parse('$baseUrl/marketplace/seller/orders').replace(queryParameters: queryParams);
    final response = await http.get(uri);

    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      final List ordersJson = data['orders'] ?? [];
      return ordersJson.map((json) => MarketFOrder.fromJson(json)).toList();
    } else {
      throw Exception('Failed to load seller orders');
    }
  }
}
