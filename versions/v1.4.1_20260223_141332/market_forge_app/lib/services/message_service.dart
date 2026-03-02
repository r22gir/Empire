import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/message.dart';

class MessageService {
  final String baseUrl;

  MessageService({this.baseUrl = 'http://localhost:8000/api'});

  /// Fetch all messages for a user
  Future<List<Message>> fetchMessages(String username) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/messages/$username'),
      );

      if (response.statusCode == 200) {
        final List<dynamic> data = json.decode(response.body);
        return data.map((json) => Message.fromJson(json)).toList();
      } else {
        throw Exception('Failed to load messages');
      }
    } catch (e) {
      // Return mock data for development
      return _getMockMessages();
    }
  }

  /// Fetch messages filtered by source
  Future<List<Message>> fetchMessagesBySource(
    String username,
    MessageSource source,
  ) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/messages/$username?source=${source.name}'),
      );

      if (response.statusCode == 200) {
        final List<dynamic> data = json.decode(response.body);
        return data.map((json) => Message.fromJson(json)).toList();
      } else {
        throw Exception('Failed to load messages');
      }
    } catch (e) {
      // Filter mock data by source
      final messages = _getMockMessages();
      return messages.where((msg) => msg.source == source).toList();
    }
  }

  /// Generate AI response for a message
  Future<String> generateAiResponse(String messageId, String username) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/messages/$username/$messageId/ai-response'),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['response'] as String;
      } else {
        throw Exception('Failed to generate AI response');
      }
    } catch (e) {
      // Return mock AI response
      return "Thanks for your interest! I'm happy to help with any questions.";
    }
  }

  /// Send a reply to a message
  Future<bool> sendReply(
    String username,
    String messageId,
    String replyText,
  ) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/messages/$username/$messageId/reply'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'reply': replyText}),
      );

      return response.statusCode == 200;
    } catch (e) {
      // Mock success
      return true;
    }
  }

  /// Mark a message as read
  Future<bool> markAsRead(String username, String messageId) async {
    try {
      final response = await http.patch(
        Uri.parse('$baseUrl/messages/$username/$messageId/read'),
      );

      return response.statusCode == 200;
    } catch (e) {
      // Mock success
      return true;
    }
  }

  /// Get unread message count
  Future<int> getUnreadCount(String username) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/messages/$username/unread-count'),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['count'] as int;
      } else {
        throw Exception('Failed to get unread count');
      }
    } catch (e) {
      // Return mock count
      return 3;
    }
  }

  /// Mock messages for development
  List<Message> _getMockMessages() {
    final now = DateTime.now();
    return [
      Message(
        id: '1',
        source: MessageSource.email,
        senderName: 'Jane Buyer',
        senderEmail: 'jane@example.com',
        subject: 'Is this still available?',
        body: "Hi! I'm interested in the vintage lamp. Is it still available?",
        timestamp: now.subtract(const Duration(hours: 2)),
        isRead: false,
        aiDraftResponse: "Yes! It's still available. Ready to ship today!",
      ),
      Message(
        id: '2',
        source: MessageSource.ebay,
        senderName: 'Bob Smith',
        senderEmail: 'bob_ebay',
        subject: 'Question about item',
        body: "What's the lowest you'll go on this?",
        listingId: 'ebay_12345',
        timestamp: now.subtract(const Duration(hours: 5)),
        isRead: false,
        aiDraftResponse: "I can do \$90.00, that's my best price.",
      ),
      Message(
        id: '3',
        source: MessageSource.facebook,
        senderName: 'Alice Johnson',
        senderEmail: 'alice_fb',
        subject: 'Shipping question',
        body: 'Can you ship to New York?',
        listingId: 'fb_67890',
        timestamp: now.subtract(const Duration(days: 1)),
        isRead: true,
      ),
      Message(
        id: '4',
        source: MessageSource.craigslist,
        senderName: 'Mike Davis',
        senderEmail: 'mike@craigslist.com',
        subject: 'Interested in your posting',
        body: 'Do you still have this available? Can I come see it today?',
        timestamp: now.subtract(const Duration(days: 2)),
        isRead: true,
      ),
    ];
  }
}
