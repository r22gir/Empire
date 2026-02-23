import 'package:flutter/material.dart';
import 'package:market_forge_app/models/product.dart';
import 'package:market_forge_app/models/listing.dart';

/// Reusable product card widget
class ProductCard extends StatelessWidget {
  final Product product;
  final ListingStatus? status;
  final VoidCallback? onTap;
  final VoidCallback? onDelete;

  const ProductCard({
    super.key,
    required this.product,
    this.status,
    this.onTap,
    this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Product image
            AspectRatio(
              aspectRatio: 1,
              child: product.photoUrls.isNotEmpty
                  ? Image.network(
                      product.photoUrls.first,
                      fit: BoxFit.cover,
                      errorBuilder: (context, error, stackTrace) {
                        return _buildPlaceholder();
                      },
                    )
                  : _buildPlaceholder(),
            ),
            
            Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Title
                  Text(
                    product.title,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  
                  const SizedBox(height: 4),
                  
                  // Price
                  Text(
                    '\$${product.price.toStringAsFixed(2)}',
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          color: Colors.green,
                          fontWeight: FontWeight.bold,
                        ),
                  ),
                  
                  const SizedBox(height: 8),
                  
                  // Category and condition
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          product.category,
                          style: Theme.of(context).textTheme.bodySmall,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      Text(
                        product.condition,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: Colors.grey,
                            ),
                      ),
                    ],
                  ),
                  
                  // Status badge if provided
                  if (status != null) ...[
                    const SizedBox(height: 8),
                    _buildStatusBadge(context),
                  ],
                ],
              ),
            ),
            
            // Delete button if provided
            if (onDelete != null)
              Padding(
                padding: const EdgeInsets.only(right: 8, bottom: 8),
                child: Align(
                  alignment: Alignment.centerRight,
                  child: IconButton(
                    icon: const Icon(Icons.delete_outline),
                    onPressed: onDelete,
                    tooltip: 'Delete',
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildPlaceholder() {
    return Container(
      color: Colors.grey[800],
      child: const Icon(
        Icons.image_outlined,
        size: 64,
        color: Colors.grey,
      ),
    );
  }

  Widget _buildStatusBadge(BuildContext context) {
    Color color;
    String text;

    switch (status!) {
      case ListingStatus.posted:
        color = Colors.green;
        text = 'Posted';
        break;
      case ListingStatus.pending:
        color = Colors.orange;
        text = 'Pending';
        break;
      case ListingStatus.failed:
        color = Colors.red;
        text = 'Failed';
        break;
      case ListingStatus.sold:
        color = Colors.blue;
        text = 'Sold';
        break;
      case ListingStatus.deleted:
        color = Colors.grey;
        text = 'Deleted';
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.2),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color),
      ),
      child: Text(
        text,
        style: TextStyle(
          color: color,
          fontSize: 12,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }
}
