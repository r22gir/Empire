import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/message.dart';
import '../providers/message_provider.dart';

class MessageDetailScreen extends StatefulWidget {
  final Message message;

  const MessageDetailScreen({
    Key? key,
    required this.message,
  }) : super(key: key);

  @override
  State<MessageDetailScreen> createState() => _MessageDetailScreenState();
}

class _MessageDetailScreenState extends State<MessageDetailScreen> {
  final TextEditingController _replyController = TextEditingController();
  bool _isGeneratingAi = false;
  bool _isSending = false;
  String? _aiDraft;

  @override
  void initState() {
    super.initState();
    // Mark as read when opening
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<MessageProvider>().markAsRead(widget.message.id);
    });

    // Set initial AI draft if available
    _aiDraft = widget.message.aiDraftResponse;
  }

  @override
  void dispose() {
    _replyController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.message.senderName),
      ),
      body: Column(
        children: [
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildMessageHeader(),
                  const SizedBox(height: 16),
                  _buildMessageBody(),
                  const SizedBox(height: 24),
                  if (widget.message.listingId != null)
                    _buildListingLink(),
                  const SizedBox(height: 24),
                  _buildAiDraftCard(),
                ],
              ),
            ),
          ),
          _buildReplySection(),
        ],
      ),
    );
  }

  Widget _buildMessageHeader() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                CircleAvatar(
                  child: Text(widget.message.senderName[0]),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        widget.message.senderName,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      Text(
                        widget.message.senderEmail,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: Colors.grey,
                            ),
                      ),
                    ],
                  ),
                ),
                _buildSourceChip(),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              widget.message.subject,
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 4),
            Text(
              _formatTimestamp(widget.message.timestamp),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Colors.grey,
                  ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSourceChip() {
    String label;
    Color color;

    switch (widget.message.source) {
      case MessageSource.email:
        label = 'Email';
        color = Colors.grey;
        break;
      case MessageSource.ebay:
        label = 'eBay';
        color = Colors.yellow.shade700;
        break;
      case MessageSource.facebook:
        label = 'Facebook';
        color = Colors.blue;
        break;
      case MessageSource.craigslist:
        label = 'Craigslist';
        color = Colors.purple;
        break;
      case MessageSource.mercari:
        label = 'Mercari';
        color = Colors.orange;
        break;
      case MessageSource.etsy:
        label = 'Etsy';
        color = Colors.orange.shade700;
        break;
      case MessageSource.amazon:
        label = 'Amazon';
        color = Colors.orange;
        break;
    }

    return Chip(
      label: Text(label),
      backgroundColor: color.withOpacity(0.2),
      labelStyle: TextStyle(color: color),
    );
  }

  Widget _buildMessageBody() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Text(
          widget.message.body,
          style: Theme.of(context).textTheme.bodyLarge,
        ),
      ),
    );
  }

  Widget _buildListingLink() {
    return Card(
      color: Colors.blue.shade50,
      child: ListTile(
        leading: const Icon(Icons.link, color: Colors.blue),
        title: const Text('Related Listing'),
        subtitle: Text(widget.message.listingId!),
        trailing: const Icon(Icons.arrow_forward_ios, size: 16),
        onTap: () {
          // TODO: Navigate to listing details
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('View listing: ${widget.message.listingId}'),
            ),
          );
        },
      ),
    );
  }

  Widget _buildAiDraftCard() {
    if (_aiDraft == null && !_isGeneratingAi) {
      return Card(
        color: Colors.purple.shade50,
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            children: [
              const Icon(Icons.auto_awesome, size: 48, color: Colors.purple),
              const SizedBox(height: 8),
              Text(
                'Generate AI Response',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      color: Colors.purple,
                    ),
              ),
              const SizedBox(height: 8),
              const Text(
                'Let AI help you craft the perfect response',
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 16),
              ElevatedButton.icon(
                onPressed: _generateAiResponse,
                icon: const Icon(Icons.auto_awesome),
                label: const Text('Generate'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.purple,
                  foregroundColor: Colors.white,
                ),
              ),
            ],
          ),
        ),
      );
    }

    if (_isGeneratingAi) {
      return Card(
        color: Colors.purple.shade50,
        child: const Padding(
          padding: EdgeInsets.all(32.0),
          child: Center(
            child: CircularProgressIndicator(),
          ),
        ),
      );
    }

    return Card(
      color: Colors.purple.shade50,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.auto_awesome, color: Colors.purple),
                const SizedBox(width: 8),
                Text(
                  'AI Draft Response',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        color: Colors.purple,
                      ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              _aiDraft!,
              style: Theme.of(context).textTheme.bodyLarge,
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () {
                      _replyController.text = _aiDraft!;
                    },
                    child: const Text('Edit'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: OutlinedButton(
                    onPressed: _generateAiResponse,
                    child: const Text('Regenerate'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: ElevatedButton(
                    onPressed: () {
                      _replyController.text = _aiDraft!;
                      _sendReply();
                    },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.purple,
                      foregroundColor: Colors.white,
                    ),
                    child: const Text('Send'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildReplySection() {
    return Container(
      decoration: BoxDecoration(
        color: Theme.of(context).scaffoldBackgroundColor,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.1),
            blurRadius: 4,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      padding: const EdgeInsets.all(16.0),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _replyController,
              decoration: const InputDecoration(
                hintText: 'Type your reply...',
                border: OutlineInputBorder(),
              ),
              maxLines: null,
              textInputAction: TextInputAction.newline,
            ),
          ),
          const SizedBox(width: 8),
          IconButton(
            onPressed: _isSending ? null : _sendReply,
            icon: _isSending
                ? const SizedBox(
                    width: 24,
                    height: 24,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.send),
            style: IconButton.styleFrom(
              backgroundColor: Colors.blue,
              foregroundColor: Colors.white,
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _generateAiResponse() async {
    setState(() {
      _isGeneratingAi = true;
    });

    try {
      await context.read<MessageProvider>().generateAiResponse(widget.message.id);
      
      // Get updated message from provider
      final provider = context.read<MessageProvider>();
      final updatedMessage = provider.messages.firstWhere(
        (msg) => msg.id == widget.message.id,
      );
      
      setState(() {
        _aiDraft = updatedMessage.aiDraftResponse;
        _isGeneratingAi = false;
      });
    } catch (e) {
      setState(() {
        _isGeneratingAi = false;
      });
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Failed to generate AI response'),
          ),
        );
      }
    }
  }

  Future<void> _sendReply() async {
    if (_replyController.text.trim().isEmpty) {
      return;
    }

    setState(() {
      _isSending = true;
    });

    try {
      final success = await context.read<MessageProvider>().sendReply(
        widget.message.id,
        _replyController.text,
      );

      setState(() {
        _isSending = false;
      });

      if (success && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Reply sent successfully!'),
            backgroundColor: Colors.green,
          ),
        );
        _replyController.clear();
      }
    } catch (e) {
      setState(() {
        _isSending = false;
      });
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Failed to send reply'),
          ),
        );
      }
    }
  }

  String _formatTimestamp(DateTime timestamp) {
    final now = DateTime.now();
    final difference = now.difference(timestamp);

    if (difference.inMinutes < 1) {
      return 'Just now';
    } else if (difference.inHours < 1) {
      return '${difference.inMinutes} minutes ago';
    } else if (difference.inDays < 1) {
      return '${difference.inHours} hours ago';
    } else if (difference.inDays < 7) {
      return '${difference.inDays} days ago';
    } else {
      return '${timestamp.month}/${timestamp.day}/${timestamp.year} at ${timestamp.hour.toString().padLeft(2, '0')}:${timestamp.minute.toString().padLeft(2, '0')}';
    }
  }
}
