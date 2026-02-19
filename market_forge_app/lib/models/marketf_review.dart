class MarketFReview {
  final String id;
  final String orderId;
  final String reviewerId;
  final String revieweeId;
  final String reviewType;
  final int rating;
  final String? title;
  final String? comment;
  final DateTime createdAt;

  MarketFReview({
    required this.id,
    required this.orderId,
    required this.reviewerId,
    required this.revieweeId,
    required this.reviewType,
    required this.rating,
    this.title,
    this.comment,
    required this.createdAt,
  });

  factory MarketFReview.fromJson(Map<String, dynamic> json) {
    return MarketFReview(
      id: json['id'],
      orderId: json['order_id'],
      reviewerId: json['reviewer_id'],
      revieweeId: json['reviewee_id'],
      reviewType: json['review_type'],
      rating: json['rating'],
      title: json['title'],
      comment: json['comment'],
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}
