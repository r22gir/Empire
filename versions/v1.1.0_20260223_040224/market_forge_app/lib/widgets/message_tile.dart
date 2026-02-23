import 'package:flutter/material.dart';
import '../models/message.dart';

class MessageTile extends StatelessWidget {
  final Message message;
  final VoidCallback onTap;

  const MessageTile({
    Key? key,
    required this.message,
    required this.onTap,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 8.0, vertical: 4.0),
      child: ListTile(
        leading: _buildSourceIcon(),
        title: Row(
          children: [
            Expanded(
              child: Text(
                message.senderName,
                style: TextStyle(
                  fontWeight: message.isRead ? FontWeight.normal : FontWeight.bold,
                ),
              ),
            ),
            if (!message.isRead)
              Container(
                width: 8,
                height: 8,
                decoration: const BoxDecoration(
                  color: Colors.blue,
                  shape: BoxShape.circle,
                ),
              ),
          ],
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              message.subject,
              style: TextStyle(
                fontWeight: message.isRead ? FontWeight.normal : FontWeight.w500,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 4),
            Text(
              message.body,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 4),
            Text(
              _formatTimestamp(message.timestamp),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Colors.grey,
                  ),
            ),
            if (message.aiDraftResponse != null) ...[
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.purple.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Row(
                  children: [
                    const Icon(
                      Icons.auto_awesome,
                      size: 16,
                      color: Colors.purple,
                    ),
                    const SizedBox(width: 4),
                    Expanded(
                      child: Text(
                        'AI Draft: ${message.aiDraftResponse}',
                        style: const TextStyle(
                          color: Colors.purple,
                          fontSize: 12,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
        onTap: onTap,
      ),
    );
  }

  Widget _buildSourceIcon() {
    IconData icon;
    Color color;

    switch (message.source) {
      case MessageSource.email:
        icon = Icons.email;
        color = Colors.grey;
        break;
      case MessageSource.ebay:
        icon = Icons.shopping_bag;
        color = Colors.yellow.shade700;
        break;
      case MessageSource.facebook:
        icon = Icons.facebook;
        color = Colors.blue;
        break;
      case MessageSource.craigslist:
        icon = Icons.list_alt;
        color = Colors.purple;
        break;
      case MessageSource.mercari:
        icon = Icons.storefront;
        color = Colors.orange;
        break;
      case MessageSource.etsy:
        icon = Icons.palette;
        color = Colors.orange.shade700;
        break;
      case MessageSource.amazon:
        icon = Icons.shopping_cart;
        color = Colors.orange;
        break;
    }

    return CircleAvatar(
      backgroundColor: color.withOpacity(0.2),
      child: Icon(icon, color: color, size: 20),
    );
  }

  String _formatTimestamp(DateTime timestamp) {
    final now = DateTime.now();
    final difference = now.difference(timestamp);

    if (difference.inMinutes < 1) {
      return 'Just now';
    } else if (difference.inHours < 1) {
      return '${difference.inMinutes}m ago';
    } else if (difference.inDays < 1) {
      return '${difference.inHours}h ago';
    } else if (difference.inDays < 7) {
      return '${difference.inDays}d ago';
    } else {
      return '${timestamp.month}/${timestamp.day}/${timestamp.year}';
    }
  }
}
