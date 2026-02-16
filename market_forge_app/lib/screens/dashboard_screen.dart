import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../models/models.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  final _apiService = ApiService();
  List<Listing> _listings = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadListings();
  }

  Future<void> _loadListings() async {
    setState(() => _isLoading = true);
    try {
      final listingsData = await _apiService.getListings();
      setState(() {
        _listings = listingsData
            .map((json) => Listing.fromJson(json))
            .toList();
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error loading listings: $e')),
        );
      }
    }
  }

  Future<void> _logout() async {
    await _apiService.logout();
    if (mounted) {
      Navigator.pushReplacementNamed(context, '/');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('My Listings'),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: () {
              // Navigate to settings
            },
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: _logout,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _listings.isEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.inventory_2, size: 64, color: Colors.grey),
                      const SizedBox(height: 16),
                      const Text(
                        'No listings yet',
                        style: TextStyle(fontSize: 18, color: Colors.grey),
                      ),
                      const SizedBox(height: 8),
                      const Text('Tap + to create your first listing'),
                    ],
                  ),
                )
              : RefreshIndicator(
                  onRefresh: _loadListings,
                  child: ListView.builder(
                    itemCount: _listings.length,
                    itemBuilder: (context, index) {
                      final listing = _listings[index];
                      return Card(
                        margin: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 8,
                        ),
                        child: ListTile(
                          title: Text(listing.title),
                          subtitle: Text(
                            '\$${listing.price.toStringAsFixed(2)} • ${_getPostedPlatforms(listing)}',
                          ),
                          trailing: const Icon(Icons.chevron_right),
                          onTap: () {
                            // Navigate to listing details
                          },
                        ),
                      );
                    },
                  ),
                ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () async {
          final result = await Navigator.pushNamed(context, '/create-listing');
          if (result == true) {
            _loadListings();
          }
        },
        icon: const Icon(Icons.add),
        label: const Text('New Listing'),
      ),
    );
  }

  String _getPostedPlatforms(Listing listing) {
    final platforms = <String>[];
    if (listing.postedEbay) platforms.add('eBay');
    if (listing.postedFacebook) platforms.add('Facebook');
    if (listing.postedPoshmark) platforms.add('Poshmark');
    if (listing.postedMercari) platforms.add('Mercari');
    if (listing.postedCraigslist) platforms.add('Craigslist');
    return platforms.isEmpty ? 'Not posted' : platforms.join(', ');
  }
}
