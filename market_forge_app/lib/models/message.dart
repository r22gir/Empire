enum MessageSource {
  email,
  ebay,
  facebook,
  craigslist,
  mercari,
  etsy,
  amazon,
}

class Message {
  final String id;
  final MessageSource source;
  final String senderName;
  final String senderEmail;
  final String subject;
  final String body;
  final String? listingId;
  final DateTime timestamp;
  final bool isRead;
  final String? aiDraftResponse;

  Message({
    required this.id,
    required this.source,
    required this.senderName,
    required this.senderEmail,
    required this.subject,
    required this.body,
    this.listingId,
    required this.timestamp,
    this.isRead = false,
    this.aiDraftResponse,
  });

  factory Message.fromJson(Map<String, dynamic> json) {
    return Message(
      id: json['id'] as String,
      source: _parseSource(json['source'] as String),
      senderName: json['sender_name'] as String,
      senderEmail: json['sender_email'] as String,
      subject: json['subject'] as String,
      body: json['body'] as String,
      listingId: json['listing_id'] as String?,
      timestamp: DateTime.parse(json['timestamp'] as String),
      isRead: json['is_read'] as bool? ?? false,
      aiDraftResponse: json['ai_draft_response'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'source': source.name,
      'sender_name': senderName,
      'sender_email': senderEmail,
      'subject': subject,
      'body': body,
      'listing_id': listingId,
      'timestamp': timestamp.toIso8601String(),
      'is_read': isRead,
      'ai_draft_response': aiDraftResponse,
    };
  }

  Message copyWith({
    String? id,
    MessageSource? source,
    String? senderName,
    String? senderEmail,
    String? subject,
    String? body,
    String? listingId,
    DateTime? timestamp,
    bool? isRead,
    String? aiDraftResponse,
  }) {
    return Message(
      id: id ?? this.id,
      source: source ?? this.source,
      senderName: senderName ?? this.senderName,
      senderEmail: senderEmail ?? this.senderEmail,
      subject: subject ?? this.subject,
      body: body ?? this.body,
      listingId: listingId ?? this.listingId,
      timestamp: timestamp ?? this.timestamp,
      isRead: isRead ?? this.isRead,
      aiDraftResponse: aiDraftResponse ?? this.aiDraftResponse,
    );
  }

  static MessageSource _parseSource(String source) {
    switch (source.toLowerCase()) {
      case 'email':
        return MessageSource.email;
      case 'ebay':
        return MessageSource.ebay;
      case 'facebook':
        return MessageSource.facebook;
      case 'craigslist':
        return MessageSource.craigslist;
      case 'mercari':
        return MessageSource.mercari;
      case 'etsy':
        return MessageSource.etsy;
      case 'amazon':
        return MessageSource.amazon;
      default:
        return MessageSource.email;
    }
  }
}
