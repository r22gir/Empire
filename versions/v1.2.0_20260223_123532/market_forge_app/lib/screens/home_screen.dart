import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:market_forge_app/providers/listing_provider.dart';
import 'package:market_forge_app/providers/user_provider.dart';
import 'package:market_forge_app/widgets/product_card.dart';
import 'package:market_forge_app/widgets/loading_overlay.dart';
import 'package:market_forge_app/screens/camera_screen.dart';

/// Home screen showing dashboard with recent listings
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  bool _isInitialized = false;

  @override
  void initState() {
    super.initState();
    _initialize();
  }

  Future<void> _initialize() async {
    if (_isInitialized) return;
    
    final listingProvider = context.read<ListingProvider>();
    final userProvider = context.read<UserProvider>();
    
    await Future.wait([
      listingProvider.initialize(),
      userProvider.initialize(),
    ]);
    
    setState(() {
      _isInitialized = true;
    });
  }

  Future<void> _refresh() async {
    await context.read<ListingProvider>().initialize();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('MarketForge'),
        actions: [
          IconButton(
            icon: const Icon(Icons.notifications_outlined),
            onPressed: () {
              // TODO: Show notifications
            },
          ),
        ],
      ),
      body: !_isInitialized
          ? const LoadingIndicator(message: 'Loading...')
          : RefreshIndicator(
              onRefresh: _refresh,
              child: Consumer<ListingProvider>(
                builder: (context, listingProvider, child) {
                  return CustomScrollView(
                    slivers: [
                      // Stats section
                      SliverToBoxAdapter(
                        child: _buildStatsSection(context, listingProvider),
                      ),
                      
                      // Listings header
                      SliverToBoxAdapter(
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(
                                'Recent Listings',
                                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                                      fontWeight: FontWeight.bold,
                                    ),
                              ),
                              Text(
                                '${listingProvider.listings.length} total',
                                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                      color: Colors.grey,
                                    ),
                              ),
                            ],
                          ),
                        ),
                      ),
                      
                      // Listings grid
                      if (listingProvider.listings.isEmpty)
                        SliverFillRemaining(
                          child: _buildEmptyState(context),
                        )
                      else
                        SliverPadding(
                          padding: const EdgeInsets.all(16),
                          sliver: SliverGrid(
                            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                              crossAxisCount: 2,
                              crossAxisSpacing: 16,
                              mainAxisSpacing: 16,
                              childAspectRatio: 0.75,
                            ),
                            delegate: SliverChildBuilderDelegate(
                              (context, index) {
                                final listing = listingProvider.listings[index];
                                return ProductCard(
                                  product: listing.product,
                                  status: listing.overallStatus,
                                  onTap: () {
                                    // TODO: Navigate to listing detail
                                  },
                                );
                              },
                              childCount: listingProvider.listings.length,
                            ),
                          ),
                        ),
                    ],
                  );
                },
              ),
            ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => const CameraScreen(),
            ),
          );
        },
        icon: const Icon(Icons.add),
        label: const Text('New Listing'),
      ),
    );
  }

  Widget _buildStatsSection(BuildContext context, ListingProvider provider) {
    return Container(
      margin: const EdgeInsets.all(16),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            Colors.deepPurple,
            Colors.deepPurple[700]!,
          ],
        ),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                child: _buildStatItem(
                  context,
                  'Total Listings',
                  provider.listings.length.toString(),
                  Icons.list_alt,
                ),
              ),
              Container(
                width: 1,
                height: 40,
                color: Colors.white24,
              ),
              Expanded(
                child: _buildStatItem(
                  context,
                  'Posted',
                  provider.totalPostedCount.toString(),
                  Icons.check_circle,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: _buildStatItem(
                  context,
                  'Failed',
                  provider.totalFailedCount.toString(),
                  Icons.error_outline,
                ),
              ),
              Container(
                width: 1,
                height: 40,
                color: Colors.white24,
              ),
              Expanded(
                child: Consumer<UserProvider>(
                  builder: (context, userProvider, child) {
                    final remaining = userProvider.remainingListings;
                    return _buildStatItem(
                      context,
                      'Remaining',
                      remaining == -1 ? '∞' : remaining.toString(),
                      Icons.inventory,
                    );
                  },
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildStatItem(
    BuildContext context,
    String label,
    String value,
    IconData icon,
  ) {
    return Column(
      children: [
        Icon(icon, color: Colors.white70, size: 28),
        const SizedBox(height: 8),
        Text(
          value,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 24,
            fontWeight: FontWeight.bold,
          ),
        ),
        Text(
          label,
          style: const TextStyle(
            color: Colors.white70,
            fontSize: 12,
          ),
        ),
      ],
    );
  }

  Widget _buildEmptyState(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.inventory_2_outlined,
            size: 80,
            color: Colors.grey[700],
          ),
          const SizedBox(height: 16),
          Text(
            'No listings yet',
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  color: Colors.grey,
                ),
          ),
          const SizedBox(height: 8),
          Text(
            'Tap the button below to create your first listing',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Colors.grey,
                ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}
