import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/shipment.dart';

class ShippingService {
  final String baseUrl;
  final String userId; // In production, get from auth
  
  ShippingService({
    this.baseUrl = 'http://localhost:8000',
    this.userId = 'test_user',
  });
  
  Future<List<ShippingRate>> getRates({
    required Address fromAddress,
    required Address toAddress,
    required Parcel parcel,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/shipping/rates'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'from_address': fromAddress.toJson(),
        'to_address': toAddress.toJson(),
        'parcel': parcel.toJson(),
      }),
    );
    
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return (data['rates'] as List)
          .map((r) => ShippingRate.fromJson(r))
          .toList();
    } else {
      throw Exception('Failed to get shipping rates');
    }
  }
  
  Future<Shipment> purchaseLabel({
    required String shipmentId,
    required String rateId,
    String? listingId,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/shipping/labels'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'shipment_id': shipmentId,
        'rate_id': rateId,
        'listing_id': listingId,
      }),
    );
    
    if (response.statusCode == 200) {
      return Shipment.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Failed to purchase label');
    }
  }
  
  Future<Shipment> getLabel(String labelId) async {
    final response = await http.get(
      Uri.parse('$baseUrl/shipping/labels/$labelId'),
    );
    
    if (response.statusCode == 200) {
      return Shipment.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Failed to get label');
    }
  }
  
  Future<TrackingInfo> trackShipment(String trackingNumber) async {
    final response = await http.get(
      Uri.parse('$baseUrl/shipping/track/$trackingNumber'),
    );
    
    if (response.statusCode == 200) {
      return TrackingInfo.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Failed to track shipment');
    }
  }
  
  Future<List<Shipment>> getHistory({
    int limit = 50,
    String? status,
  }) async {
    var url = '$baseUrl/shipping/history?user_id=$userId&limit=$limit';
    if (status != null) {
      url += '&status=$status';
    }
    
    final response = await http.get(Uri.parse(url));
    
    if (response.statusCode == 200) {
      return (jsonDecode(response.body) as List)
          .map((s) => Shipment.fromJson(s))
          .toList();
    } else {
      throw Exception('Failed to get shipment history');
    }
  }
  
  Future<void> emailLabel(String labelId, String email) async {
    final response = await http.post(
      Uri.parse('$baseUrl/shipping/labels/$labelId/email'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email}),
    );
    
    if (response.statusCode != 200) {
      throw Exception('Failed to email label');
    }
  }
}
