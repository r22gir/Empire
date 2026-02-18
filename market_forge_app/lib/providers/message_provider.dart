import 'package:flutter/foundation.dart';
import '../models/message.dart';
import '../services/message_service.dart';

class MessageProvider with ChangeNotifier {
  final MessageService _messageService;
  final String username;

  List<Message> _messages = [];
  MessageSource? _currentFilter;
  bool _isLoading = false;
  String? _error;

  MessageProvider({
    required this.username,
    MessageService? messageService,
  }) : _messageService = messageService ?? MessageService();

  // Getters
  List<Message> get messages => _messages;
  MessageSource? get currentFilter => _currentFilter;
  bool get isLoading => _isLoading;
  String? get error => _error;

  int get unreadCount =>
      _messages.where((message) => !message.isRead).length;

  List<Message> get filteredMessages {
    if (_currentFilter == null) {
      return _messages;
    }
    return _messages.where((msg) => msg.source == _currentFilter).toList();
  }

  // Load all messages
  Future<void> loadMessages() async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      if (_currentFilter == null) {
        _messages = await _messageService.fetchMessages(username);
      } else {
        _messages = await _messageService.fetchMessagesBySource(
          username,
          _currentFilter!,
        );
      }
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _error = e.toString();
      _isLoading = false;
      notifyListeners();
    }
  }

  // Set filter
  void setFilter(MessageSource? source) {
    _currentFilter = source;
    loadMessages();
  }

  // Generate AI response for a message
  Future<void> generateAiResponse(String messageId) async {
    try {
      final response = await _messageService.generateAiResponse(
        messageId,
        username,
      );

      // Update the message with AI response
      final index = _messages.indexWhere((msg) => msg.id == messageId);
      if (index != -1) {
        _messages[index] = _messages[index].copyWith(
          aiDraftResponse: response,
        );
        notifyListeners();
      }
    } catch (e) {
      _error = e.toString();
      notifyListeners();
    }
  }

  // Mark message as read
  Future<void> markAsRead(String messageId) async {
    try {
      final success = await _messageService.markAsRead(username, messageId);
      if (success) {
        final index = _messages.indexWhere((msg) => msg.id == messageId);
        if (index != -1) {
          _messages[index] = _messages[index].copyWith(isRead: true);
          notifyListeners();
        }
      }
    } catch (e) {
      _error = e.toString();
      notifyListeners();
    }
  }

  // Send reply
  Future<bool> sendReply(String messageId, String replyText) async {
    try {
      final success = await _messageService.sendReply(
        username,
        messageId,
        replyText,
      );
      if (success) {
        // Mark as read after sending
        await markAsRead(messageId);
      }
      return success;
    } catch (e) {
      _error = e.toString();
      notifyListeners();
      return false;
    }
  }

  // Refresh messages
  Future<void> refresh() async {
    await loadMessages();
  }
}
