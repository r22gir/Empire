import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:market_forge_app/providers/listing_provider.dart';
import 'package:market_forge_app/widgets/photo_thumbnail.dart';
import 'package:market_forge_app/screens/listing_status_screen.dart';
import 'package:market_forge_app/screens/camera_screen.dart';
import 'package:market_forge_app/screens/product_form_screen.dart';
import 'package:market_forge_app/screens/marketplace_picker_screen.dart';

/// Listing preview screen for reviewing before posting
class ListingPreviewScreen extends StatelessWidget {
  const ListingPreviewScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Review Listing'),
      ),
      body: Consumer<ListingProvider>(
        builder: (context, listingProvider, child) {
          final product = listingProvider.currentProduct;
          final marketplaces = listingProvider.selectedMarketplaces;

          if (product == null) {
            return const Center(
              child: Text('No product to preview'),
            );
          }

          return Column(
            children: [
              Expanded(
                child: ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    // Photos carousel
                    _buildPhotosSection(context, product.photoUrls),
                    
                    const SizedBox(height: 24),
                    
                    // Product details
                    _buildDetailsSection(context, product),
                    
                    const SizedBox(height: 24),
                    
                    // Selected marketplaces
                    _buildMarketplacesSection(context, marketplaces),
                    
                    const SizedBox(height: 24),
                  ],
                ),
              ),
              
              // Post button
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
                child: SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: listingProvider.isPosting
                        ? null
                        : () => _postListing(context, listingProvider),
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      backgroundColor: Colors.green,
                    ),
                    child: listingProvider.isPosting
                        ? const SizedBox(
                            height: 20,
                            width: 20,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                            ),
                          )
                        : Text(
                            'Post to ${marketplaces.length} Marketplace${marketplaces.length > 1 ? 's' : ''}',
                            style: const TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildPhotosSection(BuildContext context, List<String> photoUrls) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Photos',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
                TextButton.icon(
                  icon: const Icon(Icons.edit),
                  label: const Text('Edit'),
                  onPressed: () {
                    Navigator.pushReplacement(
                      context,
                      MaterialPageRoute(
                        builder: (context) => const CameraScreen(),
                      ),
                    );
                  },
                ),
              ],
            ),
            const SizedBox(height: 12),
            SizedBox(
              height: 120,
              child: ListView.builder(
                scrollDirection: Axis.horizontal,
                itemCount: photoUrls.length,
                itemBuilder: (context, index) {
                  return Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: SizedBox(
                      width: 120,
                      child: PhotoThumbnail(
                        photoPath: photoUrls[index],
                      ),
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDetailsSection(BuildContext context, product) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Details',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
                TextButton.icon(
                  icon: const Icon(Icons.edit),
                  label: const Text('Edit'),
                  onPressed: () {
                    Navigator.pushReplacement(
                      context,
                      MaterialPageRoute(
                        builder: (context) => const ProductFormScreen(),
                      ),
                    );
                  },
                ),
              ],
            ),
            const Divider(),
            _buildDetailRow(context, 'Title', product.title),
            _buildDetailRow(context, 'Price', '\$${product.price.toStringAsFixed(2)}'),
            _buildDetailRow(context, 'Category', product.category),
            _buildDetailRow(context, 'Condition', product.condition),
            _buildDetailRow(context, 'Location', product.location),
            const SizedBox(height: 8),
            Text(
              'Description',
              style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 4),
            Text(
              product.description,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDetailRow(BuildContext context, String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 100,
            child: Text(
              label,
              style: TextStyle(
                color: Colors.grey[400],
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(fontWeight: FontWeight.w500),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMarketplacesSection(BuildContext context, marketplaces) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Marketplaces',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
                TextButton.icon(
                  icon: const Icon(Icons.edit),
                  label: const Text('Edit'),
                  onPressed: () {
                    Navigator.pushReplacement(
                      context,
                      MaterialPageRoute(
                        builder: (context) => const MarketplacePickerScreen(),
                      ),
                    );
                  },
                ),
              ],
            ),
            const Divider(),
            ...marketplaces.map((marketplace) {
              return Padding(
                padding: const EdgeInsets.symmetric(vertical: 8),
                child: Row(
                  children: [
                    Icon(
                      _getMarketplaceIcon(marketplace),
                      color: Colors.deepPurple,
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        marketplace.displayName,
                        style: const TextStyle(
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                    if (marketplace.isImplemented)
                      const Icon(Icons.check_circle, color: Colors.green, size: 20)
                    else
                      const Text(
                        'Coming Soon',
                        style: TextStyle(
                          color: Colors.orange,
                          fontSize: 12,
                        ),
                      ),
                  ],
                ),
              );
            }).toList(),
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

  Future<void> _postListing(
    BuildContext context,
    ListingProvider listingProvider,
  ) async {
    try {
      final listing = await listingProvider.postListing();
      
      if (!context.mounted) return;

      // Navigate to status screen
      Navigator.pushAndRemoveUntil(
        context,
        MaterialPageRoute(
          builder: (context) => ListingStatusScreen(listing: listing),
        ),
        (route) => route.isFirst, // Keep only home screen in stack
      );
    } catch (e) {
      if (!context.mounted) return;
      
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Error posting listing: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }
}
