import 'package:flutter/material.dart';
import 'package:market_forge_app/models/marketplace.dart';

/// Marketplace selector chip widget
class MarketplaceChip extends StatelessWidget {
  final Marketplace marketplace;
  final bool isSelected;
  final bool isConnected;
  final VoidCallback onTap;

  const MarketplaceChip({
    super.key,
    required this.marketplace,
    required this.isSelected,
    required this.isConnected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final isImplemented = marketplace.isImplemented;
    
    return InkWell(
      onTap: isImplemented ? onTap : null,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: isSelected
              ? Colors.deepPurple.withOpacity(0.2)
              : Theme.of(context).cardTheme.color,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isSelected ? Colors.deepPurple : Colors.grey[700]!,
            width: 2,
          ),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Icon or placeholder
            Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                color: Colors.grey[800],
                borderRadius: BorderRadius.circular(8),
              ),
              child: Center(
                child: Icon(
                  _getIcon(),
                  size: 32,
                  color: isImplemented ? Colors.white : Colors.grey,
                ),
              ),
            ),
            
            const SizedBox(height: 12),
            
            // Marketplace name
            Text(
              marketplace.displayName,
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: isImplemented ? null : Colors.grey,
                  ),
              textAlign: TextAlign.center,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            
            const SizedBox(height: 8),
            
            // Status indicators
            if (!isImplemented)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.orange.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: const Text(
                  'Coming Soon',
                  style: TextStyle(
                    color: Colors.orange,
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              )
            else if (isConnected)
              const Icon(
                Icons.check_circle,
                color: Colors.green,
                size: 20,
              )
            else
              const Text(
                'Not Connected',
                style: TextStyle(
                  color: Colors.grey,
                  fontSize: 10,
                ),
              ),
          ],
        ),
      ),
    );
  }

  IconData _getIcon() {
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
    }
  }
}
