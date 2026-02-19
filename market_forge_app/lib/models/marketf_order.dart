class MarketFOrder {
  final String id;
  final String orderNumber;
  final String buyerId;
  final String sellerId;
  final String productId;
  final String productTitle;
  final double productPrice;
  final double shippingPrice;
  final Map<String, dynamic> shippingAddress;
  final String? trackingNumber;
  final String? carrier;
  final String? shipmentId;
  final double subtotal;
  final double marketplaceFee;
  final double paymentProcessingFee;
  final double total;
  final double sellerPayout;
  final String escrowStatus;
  final DateTime? escrowHeldAt;
  final DateTime? escrowReleasedAt;
  final String status;
  final DateTime createdAt;
  final DateTime? paidAt;
  final DateTime? shippedAt;
  final DateTime? deliveredAt;
  final DateTime? completedAt;

  MarketFOrder({
    required this.id,
    required this.orderNumber,
    required this.buyerId,
    required this.sellerId,
    required this.productId,
    required this.productTitle,
    required this.productPrice,
    required this.shippingPrice,
    required this.shippingAddress,
    this.trackingNumber,
    this.carrier,
    this.shipmentId,
    required this.subtotal,
    required this.marketplaceFee,
    required this.paymentProcessingFee,
    required this.total,
    required this.sellerPayout,
    required this.escrowStatus,
    this.escrowHeldAt,
    this.escrowReleasedAt,
    required this.status,
    required this.createdAt,
    this.paidAt,
    this.shippedAt,
    this.deliveredAt,
    this.completedAt,
  });

  factory MarketFOrder.fromJson(Map<String, dynamic> json) {
    return MarketFOrder(
      id: json['id'],
      orderNumber: json['order_number'],
      buyerId: json['buyer_id'],
      sellerId: json['seller_id'],
      productId: json['product_id'],
      productTitle: json['product_title'],
      productPrice: json['product_price'].toDouble(),
      shippingPrice: json['shipping_price'].toDouble(),
      shippingAddress: json['shipping_address'],
      trackingNumber: json['tracking_number'],
      carrier: json['carrier'],
      shipmentId: json['shipment_id'],
      subtotal: json['subtotal'].toDouble(),
      marketplaceFee: json['marketplace_fee'].toDouble(),
      paymentProcessingFee: json['payment_processing_fee'].toDouble(),
      total: json['total'].toDouble(),
      sellerPayout: json['seller_payout'].toDouble(),
      escrowStatus: json['escrow_status'],
      escrowHeldAt: json['escrow_held_at'] != null ? DateTime.parse(json['escrow_held_at']) : null,
      escrowReleasedAt: json['escrow_released_at'] != null ? DateTime.parse(json['escrow_released_at']) : null,
      status: json['status'],
      createdAt: DateTime.parse(json['created_at']),
      paidAt: json['paid_at'] != null ? DateTime.parse(json['paid_at']) : null,
      shippedAt: json['shipped_at'] != null ? DateTime.parse(json['shipped_at']) : null,
      deliveredAt: json['delivered_at'] != null ? DateTime.parse(json['delivered_at']) : null,
      completedAt: json['completed_at'] != null ? DateTime.parse(json['completed_at']) : null,
    );
  }
}
