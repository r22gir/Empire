import 'package:flutter/material.dart';
import '../models/shipment.dart';
import '../services/shipping_service.dart';

class ShippingProvider with ChangeNotifier {
  final ShippingService _service = ShippingService();
  
  List<Shipment> _recentShipments = [];
  bool _isLoading = false;
  String? _error;
  
  List<Shipment> get recentShipments => _recentShipments;
  bool get isLoading => _isLoading;
  String? get error => _error;
  
  Future<void> loadHistory({String? status}) async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    
    try {
      _recentShipments = await _service.getHistory(status: status);
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _error = e.toString();
      _isLoading = false;
      notifyListeners();
    }
  }
  
  Future<List<ShippingRate>> getRates({
    required Address fromAddress,
    required Address toAddress,
    required Parcel parcel,
  }) async {
    return await _service.getRates(
      fromAddress: fromAddress,
      toAddress: toAddress,
      parcel: parcel,
    );
  }
  
  Future<Shipment> purchaseLabel({
    required String shipmentId,
    required String rateId,
    String? listingId,
  }) async {
    final shipment = await _service.purchaseLabel(
      shipmentId: shipmentId,
      rateId: rateId,
      listingId: listingId,
    );
    
    // Add to recent shipments
    _recentShipments.insert(0, shipment);
    notifyListeners();
    
    return shipment;
  }
  
  Future<TrackingInfo> trackShipment(String trackingNumber) async {
    return await _service.trackShipment(trackingNumber);
  }
}
