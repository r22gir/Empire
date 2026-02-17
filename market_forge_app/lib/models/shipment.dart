class Shipment {
  final String id;
  final String userId;
  
  // Addresses
  final Address fromAddress;
  final Address toAddress;
  
  // Package details
  final Parcel parcel;
  
  // Shipping details
  final String carrier;
  final String service;
  final String trackingNumber;
  
  // Label URLs
  final String labelUrl;
  final String labelPdfUrl;
  
  // Costs
  final double baseRate;
  final double ourPrice;
  
  // Status
  final String status;
  
  // Metadata
  final String? listingId;
  final DateTime createdAt;
  final DateTime updatedAt;
  
  Shipment({
    required this.id,
    required this.userId,
    required this.fromAddress,
    required this.toAddress,
    required this.parcel,
    required this.carrier,
    required this.service,
    required this.trackingNumber,
    required this.labelUrl,
    required this.labelPdfUrl,
    required this.baseRate,
    required this.ourPrice,
    required this.status,
    this.listingId,
    required this.createdAt,
    required this.updatedAt,
  });
  
  factory Shipment.fromJson(Map<String, dynamic> json) {
    return Shipment(
      id: json['id'],
      userId: json['user_id'],
      fromAddress: Address.fromJson(json['from_address'] ?? {
        'name': json['from_name'],
        'street1': json['from_street1'],
        'street2': json['from_street2'],
        'city': json['from_city'],
        'state': json['from_state'],
        'zip': json['from_zip'],
        'country': json['from_country'] ?? 'US',
      }),
      toAddress: Address.fromJson(json['to_address'] ?? {
        'name': json['to_name'],
        'street1': json['to_street1'],
        'street2': json['to_street2'],
        'city': json['to_city'],
        'state': json['to_state'],
        'zip': json['to_zip'],
        'country': json['to_country'] ?? 'US',
      }),
      parcel: Parcel(
        length: (json['length'] as num).toDouble(),
        width: (json['width'] as num).toDouble(),
        height: (json['height'] as num).toDouble(),
        weight: (json['weight'] as num).toDouble(),
      ),
      carrier: json['carrier'],
      service: json['service'],
      trackingNumber: json['tracking_number'],
      labelUrl: json['label_url'],
      labelPdfUrl: json['label_pdf_url'],
      baseRate: (json['base_rate'] as num).toDouble(),
      ourPrice: (json['our_price'] as num).toDouble(),
      status: json['status'],
      listingId: json['listing_id'],
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
    );
  }
  
  double get savings => baseRate - ourPrice;
}

class Address {
  final String name;
  final String street1;
  final String? street2;
  final String city;
  final String state;
  final String zip;
  final String country;
  
  Address({
    required this.name,
    required this.street1,
    this.street2,
    required this.city,
    required this.state,
    required this.zip,
    this.country = 'US',
  });
  
  factory Address.fromJson(Map<String, dynamic> json) {
    return Address(
      name: json['name'],
      street1: json['street1'],
      street2: json['street2'],
      city: json['city'],
      state: json['state'],
      zip: json['zip'],
      country: json['country'] ?? 'US',
    );
  }
  
  Map<String, dynamic> toJson() {
    return {
      'name': name,
      'street1': street1,
      'street2': street2,
      'city': city,
      'state': state,
      'zip': zip,
      'country': country,
    };
  }
}

class Parcel {
  final double length;
  final double width;
  final double height;
  final double weight;
  
  Parcel({
    required this.length,
    required this.width,
    required this.height,
    required this.weight,
  });
  
  Map<String, dynamic> toJson() {
    return {
      'length': length,
      'width': width,
      'height': height,
      'weight': weight,
    };
  }
}

class ShippingRate {
  final String carrier;
  final String service;
  final double rate;
  final double ourPrice;
  final int? deliveryDays;
  final String shipmentId;
  final String rateId;
  
  ShippingRate({
    required this.carrier,
    required this.service,
    required this.rate,
    required this.ourPrice,
    this.deliveryDays,
    required this.shipmentId,
    required this.rateId,
  });
  
  factory ShippingRate.fromJson(Map<String, dynamic> json) {
    return ShippingRate(
      carrier: json['carrier'],
      service: json['service'],
      rate: (json['rate'] as num).toDouble(),
      ourPrice: (json['our_price'] as num).toDouble(),
      deliveryDays: json['delivery_days'],
      shipmentId: json['shipment_id'],
      rateId: json['rate_id'],
    );
  }
  
  double get savings => rate - ourPrice;
}

class TrackingInfo {
  final String status;
  final String? statusDetail;
  final List<TrackingEvent> events;
  
  TrackingInfo({
    required this.status,
    this.statusDetail,
    required this.events,
  });
  
  factory TrackingInfo.fromJson(Map<String, dynamic> json) {
    return TrackingInfo(
      status: json['status'],
      statusDetail: json['status_detail'],
      events: (json['events'] as List)
          .map((e) => TrackingEvent.fromJson(e))
          .toList(),
    );
  }
}

class TrackingEvent {
  final String datetime;
  final String message;
  final String? city;
  final String? state;
  
  TrackingEvent({
    required this.datetime,
    required this.message,
    this.city,
    this.state,
  });
  
  factory TrackingEvent.fromJson(Map<String, dynamic> json) {
    return TrackingEvent(
      datetime: json['datetime'],
      message: json['message'],
      city: json['city'],
      state: json['state'],
    );
  }
}
