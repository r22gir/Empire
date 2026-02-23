import 'package:flutter/material.dart';
import 'package:market_forge_app/models/listing.dart';
import 'package:market_forge_app/widgets/status_badge.dart';

/// Listing status screen showing success/failure per marketplace
class ListingStatusScreen extends StatelessWidget {
  final Listing listing;

  const ListingStatusScreen({
    super.key,
    required this.listing,
  });

  @override
  Widget build(BuildContext context) {
    final successCount = listing.postedCount;
    final failedCount = listing.failedCount;
    final totalCount = listing.marketplaceStatuses.length;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Listing Status'),
      ),
      body: Column(
        children: [
          // Overall status card
          Container(
            width: double.infinity,
            margin: const EdgeInsets.all(16),
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: successCount == totalCount
                    ? [Colors.green, Colors.green[700]!]
                    : failedCount == totalCount
                        ? [Colors.red, Colors.red[700]!]
                        : [Colors.orange, Colors.orange[700]!],
              ),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Column(
              children: [
                Icon(
                  successCount == totalCount
                      ? Icons.check_circle_outline
                      : failedCount == totalCount
                          ? Icons.error_outline
                          : Icons.info_outline,
                  size: 64,
                  color: Colors.white,
                ),
                const SizedBox(height: 16),
                Text(
                  successCount == totalCount
                      ? 'All Listings Posted!'
                      : failedCount == totalCount
                          ? 'Listing Failed'
                          : 'Partially Posted',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 24,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  '$successCount of $totalCount marketplace${totalCount > 1 ? 's' : ''} succeeded',
                  style: const TextStyle(
                    color: Colors.white70,
                    fontSize: 16,
                  ),
                ),
              ],
            ),
          ),
          
          // Marketplace statuses
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              itemCount: listing.marketplaceStatuses.length,
              itemBuilder: (context, index) {
                final status = listing.marketplaceStatuses[index];
                return _buildMarketplaceStatusCard(context, status);
              },
            ),
          ),
          
          // Action buttons
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Theme.of(context).cardTheme.color,
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.2),
                  blurRadius: 8,
                  offset: const Offset(0, -2),
                ),
              ],
            ),
            child: Column(
              children: [
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: () {
                      Navigator.popUntil(context, (route) => route.isFirst);
                    },
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 16),
                    ),
                    child: const Text(
                      'Done',
                      style: TextStyle(fontSize: 16),
                    ),
                  ),
                ),
                if (failedCount > 0) ...[
                  const SizedBox(height: 8),
                  SizedBox(
                    width: double.infinity,
                    child: OutlinedButton(
                      onPressed: () {
                        // TODO: Implement retry logic
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text('Retry functionality coming soon'),
                          ),
                        );
                      },
                      style: OutlinedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 16),
                      ),
                      child: const Text(
                        'Retry Failed Listings',
                        style: TextStyle(fontSize: 16),
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMarketplaceStatusCard(
    BuildContext context,
    MarketplaceListingStatus status,
  ) {
    final isSuccess = status.status == ListingStatus.posted;
    final isFailed = status.status == ListingStatus.failed;

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  _getMarketplaceIcon(status.marketplace),
                  size: 32,
                  color: Colors.deepPurple,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        status.marketplace.displayName,
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.bold,
                            ),
                      ),
                      const SizedBox(height: 4),
                      StatusBadge(status: status.status),
                    ],
                  ),
                ),
              ],
            ),
            
            if (isSuccess && status.listingUrl != null) ...[
              const SizedBox(height: 12),
              const Divider(),
              TextButton.icon(
                icon: const Icon(Icons.open_in_new, size: 18),
                label: const Text('View on Marketplace'),
                onPressed: () {
                  // TODO: Open URL in browser
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text('Opening: ${status.listingUrl}'),
                    ),
                  );
                },
              ),
            ],
            
            if (isFailed && status.errorMessage != null) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.red.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.red.withOpacity(0.3)),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.error_outline, color: Colors.red, size: 20),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        status.errorMessage!,
                        style: const TextStyle(color: Colors.red),
                      ),
                    ),
                  ],
                ),
              ),
            ],
            
            // Timestamp
            const SizedBox(height: 8),
            Text(
              'Posted at ${_formatTime(status.timestamp)}',
              style: TextStyle(
                color: Colors.grey[600],
                fontSize: 12,
              ),
            ),
          ],
        ),
      ),
    );
  }

  IconData _getMarketplaceIcon(marketplace) {
    switch (marketplace) {
      case Marketplace.facebookMarketplace:
        return Icons.facebook;
      case Marketplace.ebay:
        return Icons.shopping_bag;
      case Marketplace.craigslist:
        return Icons.list;
      case Marketplace.amazon:
        return Icons.shopping_cart;
      case Marketplace.etsy:
        return Icons.storefront;
      case Marketplace.mercari:
        return Icons.local_shipping;
      default:
        return Icons.store;
    }
  }

  String _formatTime(DateTime time) {
    final now = DateTime.now();
    final difference = now.difference(time);

    if (difference.inSeconds < 60) {
      return 'just now';
    } else if (difference.inMinutes < 60) {
      return '${difference.inMinutes} minute${difference.inMinutes > 1 ? 's' : ''} ago';
    } else if (difference.inHours < 24) {
      return '${difference.inHours} hour${difference.inHours > 1 ? 's' : ''} ago';
    } else {
      return '${time.month}/${time.day}/${time.year} at ${time.hour}:${time.minute.toString().padLeft(2, '0')}';
    }
  }
}
