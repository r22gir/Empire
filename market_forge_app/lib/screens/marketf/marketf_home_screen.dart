import 'package:flutter/material.dart';
import '../../services/marketf_service.dart';
import '../../models/marketf_product.dart';
import '../../widgets/marketf/product_card.dart';

class MarketFHomeScreen extends StatefulWidget {
  @override
  _MarketFHomeScreenState createState() => _MarketFHomeScreenState();
}

class _MarketFHomeScreenState extends State<MarketFHomeScreen> {
  final MarketFService _marketfService = MarketFService();
  List<MarketFProduct> _products = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadProducts();
  }

  Future<void> _loadProducts() async {
    try {
      final products = await _marketfService.getProducts();
      setState(() {
        _products = products;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _loading = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to load products: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            Text('🛒', style: TextStyle(fontSize: 24)),
            SizedBox(width: 8),
            Text('MarketF', style: TextStyle(fontWeight: FontWeight.bold)),
          ],
        ),
        actions: [
          IconButton(
            icon: Icon(Icons.search),
            onPressed: () {
              // Navigate to search
            },
          ),
          IconButton(
            icon: Icon(Icons.shopping_cart),
            onPressed: () {
              // Navigate to cart
            },
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadProducts,
        child: _loading
            ? Center(child: CircularProgressIndicator())
            : SingleChildScrollView(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Hero Banner
                    Container(
                      padding: EdgeInsets.all(24),
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          colors: [Color(0xFF0066FF), Color(0xFF0052CC)],
                        ),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Buy & Sell with Only 8% Fees',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 24,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          SizedBox(height: 8),
                          Text(
                            'Save 4.9% vs eBay on every sale',
                            style: TextStyle(color: Colors.white70, fontSize: 16),
                          ),
                          SizedBox(height: 16),
                          Row(
                            children: [
                              ElevatedButton(
                                onPressed: () {},
                                child: Text('Start Shopping'),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: Color(0xFFFF6600),
                                ),
                              ),
                              SizedBox(width: 12),
                              ElevatedButton(
                                onPressed: () {},
                                child: Text('Start Selling'),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: Colors.white,
                                  foregroundColor: Color(0xFF0066FF),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),

                    // Categories
                    Container(
                      padding: EdgeInsets.symmetric(vertical: 16),
                      child: SingleChildScrollView(
                        scrollDirection: Axis.horizontal,
                        child: Row(
                          children: [
                            _buildCategoryChip('📱', 'Electronics'),
                            _buildCategoryChip('👗', 'Clothing'),
                            _buildCategoryChip('🏠', 'Home'),
                            _buildCategoryChip('⚽', 'Sports'),
                            _buildCategoryChip('🎨', 'Collectibles'),
                          ],
                        ),
                      ),
                    ),

                    // Featured Products
                    Padding(
                      padding: EdgeInsets.all(16),
                      child: Text(
                        '🔥 Featured Deals',
                        style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                      ),
                    ),

                    GridView.builder(
                      shrinkWrap: true,
                      physics: NeverScrollableScrollPhysics(),
                      padding: EdgeInsets.symmetric(horizontal: 16),
                      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: 2,
                        childAspectRatio: 0.7,
                        crossAxisSpacing: 16,
                        mainAxisSpacing: 16,
                      ),
                      itemCount: _products.length,
                      itemBuilder: (context, index) {
                        return ProductCard(product: _products[index]);
                      },
                    ),

                    SizedBox(height: 24),
                  ],
                ),
              ),
      ),
    );
  }

  Widget _buildCategoryChip(String icon, String label) {
    return Padding(
      padding: EdgeInsets.symmetric(horizontal: 8),
      child: InkWell(
        onTap: () {},
        child: Chip(
          avatar: Text(icon, style: TextStyle(fontSize: 18)),
          label: Text(label),
        ),
      ),
    );
  }
}
