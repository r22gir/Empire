import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/shipping_provider.dart';
import '../models/shipment.dart';
import 'shipping/create_shipment_screen.dart';
import 'shipping/shipment_history_screen.dart';

class ShippingScreen extends StatefulWidget {
  @override
  _ShippingScreenState createState() => _ShippingScreenState();
}

class _ShippingScreenState extends State<ShippingScreen> {
  @override
  void initState() {
    super.initState();
    // Load recent shipments
    Future.microtask(() => 
      Provider.of<ShippingProvider>(context, listen: false).loadHistory()
    );
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('ShipForge'),
        backgroundColor: Colors.orange,
        actions: [
          IconButton(
            icon: Icon(Icons.history),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => ShipmentHistoryScreen()),
              );
            },
          ),
        ],
      ),
      body: Consumer<ShippingProvider>(
        builder: (context, provider, child) {
          if (provider.isLoading) {
            return Center(child: CircularProgressIndicator());
          }
          
          return SingleChildScrollView(
            padding: EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Stats Card
                _buildStatsCard(provider),
                SizedBox(height: 24),
                
                // Recent Shipments
                _buildRecentShipments(provider),
              ],
            ),
          );
        },
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () {
          Navigator.push(
            context,
            MaterialPageRoute(builder: (context) => CreateShipmentScreen()),
          );
        },
        icon: Icon(Icons.add),
        label: Text('New Shipment'),
        backgroundColor: Colors.orange,
      ),
    );
  }
  
  Widget _buildStatsCard(ShippingProvider provider) {
    final recentShipments = provider.recentShipments;
    final thisMonth = recentShipments.where((s) {
      final now = DateTime.now();
      return s.createdAt.year == now.year && s.createdAt.month == now.month;
    }).length;
    
    final totalSavings = recentShipments.fold(
      0.0, 
      (sum, s) => sum + s.savings
    );
    
    return Card(
      elevation: 4,
      child: Padding(
        padding: EdgeInsets.all(16),
        child: Column(
          children: [
            Text(
              'Shipping Stats',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _buildStatItem(
                  'Total Shipped',
                  recentShipments.length.toString(),
                  Icons.local_shipping,
                  Colors.blue,
                ),
                _buildStatItem(
                  'This Month',
                  thisMonth.toString(),
                  Icons.calendar_today,
                  Colors.green,
                ),
                _buildStatItem(
                  'Saved',
                  '\$${totalSavings.toStringAsFixed(2)}',
                  Icons.savings,
                  Colors.orange,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildStatItem(String label, String value, IconData icon, Color color) {
    return Column(
      children: [
        Icon(icon, color: color, size: 32),
        SizedBox(height: 8),
        Text(
          value,
          style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: color),
        ),
        Text(label, style: TextStyle(fontSize: 12, color: Colors.grey)),
      ],
    );
  }
  
  Widget _buildRecentShipments(ShippingProvider provider) {
    final recent = provider.recentShipments.take(5).toList();
    
    if (recent.isEmpty) {
      return Card(
        child: Padding(
          padding: EdgeInsets.all(32),
          child: Column(
            children: [
              Icon(Icons.inbox, size: 64, color: Colors.grey),
              SizedBox(height: 16),
              Text(
                'No shipments yet',
                style: TextStyle(fontSize: 18, color: Colors.grey),
              ),
              SizedBox(height: 8),
              Text(
                'Create your first shipment to get started',
                style: TextStyle(color: Colors.grey),
              ),
            ],
          ),
        ),
      );
    }
    
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Recent Shipments',
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
        ),
        SizedBox(height: 12),
        ...recent.map((shipment) => _buildShipmentCard(shipment)),
      ],
    );
  }
  
  Widget _buildShipmentCard(Shipment shipment) {
    return Card(
      margin: EdgeInsets.only(bottom: 12),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: _getStatusColor(shipment.status),
          child: Icon(Icons.local_shipping, color: Colors.white),
        ),
        title: Text(
          '${shipment.carrier} ${shipment.service}',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(shipment.trackingNumber),
            Text(
              'To: ${shipment.toAddress.city}, ${shipment.toAddress.state}',
              style: TextStyle(fontSize: 12),
            ),
          ],
        ),
        trailing: Text(
          '\$${shipment.ourPrice.toStringAsFixed(2)}',
          style: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.bold,
            color: Colors.green,
          ),
        ),
        onTap: () {
          // Navigate to label preview
          _showLabelDialog(shipment);
        },
      ),
    );
  }
  
  Color _getStatusColor(String status) {
    switch (status) {
      case 'delivered':
        return Colors.green;
      case 'in_transit':
        return Colors.blue;
      case 'pending':
        return Colors.orange;
      default:
        return Colors.grey;
    }
  }
  
  void _showLabelDialog(Shipment shipment) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Shipment Details'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Tracking: ${shipment.trackingNumber}'),
            SizedBox(height: 8),
            Text('Status: ${shipment.status}'),
            SizedBox(height: 8),
            Text('Cost: \$${shipment.ourPrice.toStringAsFixed(2)}'),
            SizedBox(height: 8),
            Text('Savings: \$${shipment.savings.toStringAsFixed(2)}'),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('Close'),
          ),
          ElevatedButton(
            onPressed: () {
              // TODO: Navigate to label preview screen
              Navigator.pop(context);
            },
            child: Text('View Label'),
          ),
        ],
      ),
    );
  }
}
