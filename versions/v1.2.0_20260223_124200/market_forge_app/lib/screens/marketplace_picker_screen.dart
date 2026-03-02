import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:market_forge_app/providers/listing_provider.dart';
import 'package:market_forge_app/models/marketplace.dart';
import 'package:market_forge_app/widgets/marketplace_chip.dart';
import 'package:market_forge_app/screens/listing_preview_screen.dart';

/// Marketplace picker screen for selecting target marketplaces
class MarketplacePickerScreen extends StatefulWidget {
  const MarketplacePickerScreen({super.key});

  @override
  State<MarketplacePickerScreen> createState() => _MarketplacePickerScreenState();
}

class _MarketplacePickerScreenState extends State<MarketplacePickerScreen> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Select Marketplaces'),
      ),
      body: Consumer<ListingProvider>(
        builder: (context, listingProvider, child) {
          return Column(
            children: [
              // Instructions
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                color: Colors.deepPurple.withOpacity(0.1),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Choose where to list your product',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Select one or more marketplaces. Your product will be posted to all selected platforms.',
                      style: TextStyle(
                        color: Colors.grey[400],
                      ),
                    ),
                  ],
                ),
              ),
              
              // Marketplace grid
              Expanded(
                child: GridView.builder(
                  padding: const EdgeInsets.all(16),
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 2,
                    crossAxisSpacing: 16,
                    mainAxisSpacing: 16,
                    childAspectRatio: 0.9,
                  ),
                  itemCount: Marketplace.values.length,
                  itemBuilder: (context, index) {
                    final marketplace = Marketplace.values[index];
                    final service = listingProvider.getService(marketplace);
                    final isSelected = listingProvider.selectedMarketplaces.contains(marketplace);
                    
                    return MarketplaceChip(
                      marketplace: marketplace,
                      isSelected: isSelected,
                      isConnected: service.isConnected,
                      onTap: () {
                        setState(() {
                          listingProvider.toggleMarketplace(marketplace);
                        });
                      },
                    );
                  },
                ),
              ),
              
              // Selected count and continue button
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
                    // Selected count
                    if (listingProvider.selectedMarketplaces.isNotEmpty)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: Text(
                          '${listingProvider.selectedMarketplaces.length} marketplace(s) selected',
                          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                color: Colors.grey,
                              ),
                        ),
                      ),
                    
                    // Continue button
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton(
                        onPressed: listingProvider.selectedMarketplaces.isEmpty
                            ? null
                            : _continue,
                        style: ElevatedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 16),
                        ),
                        child: Text(
                          listingProvider.selectedMarketplaces.isEmpty
                              ? 'Select at least one marketplace'
                              : 'Continue to Preview',
                          style: const TextStyle(fontSize: 16),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  void _continue() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => const ListingPreviewScreen(),
      ),
    );
  }
}
