import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/message.dart';
import '../providers/message_provider.dart';
import '../widgets/message_tile.dart';
import 'message_detail_screen.dart';

class MessagesScreen extends StatefulWidget {
  const MessagesScreen({Key? key}) : super(key: key);

  @override
  State<MessagesScreen> createState() => _MessagesScreenState();
}

class _MessagesScreenState extends State<MessagesScreen> {
  MessageSource? _selectedFilter;

  @override
  void initState() {
    super.initState();
    // Load messages when screen initializes
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<MessageProvider>().loadMessages();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Messages'),
        actions: [
          PopupMenuButton<MessageSource?>(
            icon: const Icon(Icons.filter_list),
            onSelected: (source) {
              setState(() {
                _selectedFilter = source;
              });
              context.read<MessageProvider>().setFilter(source);
            },
            itemBuilder: (context) => [
              const PopupMenuItem(
                value: null,
                child: Text('All Messages'),
              ),
              const PopupMenuDivider(),
              const PopupMenuItem(
                value: MessageSource.email,
                child: Text('📧 Email'),
              ),
              const PopupMenuItem(
                value: MessageSource.ebay,
                child: Text('🛍️ eBay'),
              ),
              const PopupMenuItem(
                value: MessageSource.facebook,
                child: Text('📘 Facebook'),
              ),
              const PopupMenuItem(
                value: MessageSource.craigslist,
                child: Text('📋 Craigslist'),
              ),
              const PopupMenuItem(
                value: MessageSource.mercari,
                child: Text('🏪 Mercari'),
              ),
              const PopupMenuItem(
                value: MessageSource.etsy,
                child: Text('🎨 Etsy'),
              ),
              const PopupMenuItem(
                value: MessageSource.amazon,
                child: Text('📦 Amazon'),
              ),
            ],
          ),
        ],
      ),
      body: Consumer<MessageProvider>(
        builder: (context, provider, child) {
          if (provider.isLoading) {
            return const Center(
              child: CircularProgressIndicator(),
            );
          }

          if (provider.error != null) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(
                    Icons.error_outline,
                    color: Colors.red,
                    size: 60,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Error loading messages',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    provider.error!,
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 16),
                  ElevatedButton(
                    onPressed: () => provider.refresh(),
                    child: const Text('Retry'),
                  ),
                ],
              ),
            );
          }

          final messages = provider.filteredMessages;

          if (messages.isEmpty) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    Icons.chat_bubble_outline,
                    size: 80,
                    color: Colors.grey.shade400,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    _selectedFilter == null
                        ? 'No messages yet'
                        : 'No ${_getSourceName(_selectedFilter!)} messages',
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          color: Colors.grey.shade600,
                        ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'When you receive messages, they\'ll appear here',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: Colors.grey.shade500,
                        ),
                  ),
                ],
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: () => provider.refresh(),
            child: ListView.builder(
              itemCount: messages.length,
              itemBuilder: (context, index) {
                final message = messages[index];
                return MessageTile(
                  message: message,
                  onTap: () {
                    Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (context) => MessageDetailScreen(
                          message: message,
                        ),
                      ),
                    );
                  },
                );
              },
            ),
          );
        },
      ),
    );
  }

  String _getSourceName(MessageSource source) {
    switch (source) {
      case MessageSource.email:
        return 'Email';
      case MessageSource.ebay:
        return 'eBay';
      case MessageSource.facebook:
        return 'Facebook';
      case MessageSource.craigslist:
        return 'Craigslist';
      case MessageSource.mercari:
        return 'Mercari';
      case MessageSource.etsy:
        return 'Etsy';
      case MessageSource.amazon:
        return 'Amazon';
    }
  }
}
