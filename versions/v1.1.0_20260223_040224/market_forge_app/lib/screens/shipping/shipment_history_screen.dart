import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../providers/shipping_provider.dart';
import '../../models/shipment.dart';

class ShipmentHistoryScreen extends StatefulWidget {
  @override
  _ShipmentHistoryScreenState createState() => _ShipmentHistoryScreenState();
}

class _ShipmentHistoryScreenState extends State<ShipmentHistoryScreen> {
  String? _filterStatus;
  
  @override
  void initState() {
    super.initState();
    _loadHistory();
  }
  
  Future<void> _loadHistory() async {
    await Provider.of<ShippingProvider>(context, listen: false)
        .loadHistory(status: _filterStatus);
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Shipment History'),
        backgroundColor: Colors.orange,
        actions: [
          PopupMenuButton<String>(
            onSelected: (value) {
              setState(() {
                _filterStatus = value == 'all' ? null : value;
              });
              _loadHistory();
            },
            itemBuilder: (context) => [
              PopupMenuItem(value: 'all', child: Text('All')),
              PopupMenuItem(value: 'pending', child: Text('Pending')),
              PopupMenuItem(value: 'in_transit', child: Text('In Transit')),
              PopupMenuItem(value: 'delivered', child: Text('Delivered')),
            ],
          ),
        ],
      ),
      body: Consumer<ShippingProvider>(
        builder: (context, provider, child) {
          if (provider.isLoading) {
            return Center(child: CircularProgressIndicator());
          }
          
          final shipments = provider.recentShipments;
          
          if (shipments.isEmpty) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.inbox, size: 64, color: Colors.grey),
                  SizedBox(height: 16),
                  Text('No shipments found'),
                ],
              ),
            );
          }
          
          return ListView.builder(
            padding: EdgeInsets.all(16),
            itemCount: shipments.length,
            itemBuilder: (context, index) {
              final shipment = shipments[index];
              return _buildShipmentCard(shipment);
            },
          );
        },
      ),
    );
  }
  
  Widget _buildShipmentCard(Shipment shipment) {
    return Card(
      margin: EdgeInsets.only(bottom: 12),
      child: ExpansionTile(
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
              shipment.createdAt.toString().split('.')[0],
              style: TextStyle(fontSize: 11, color: Colors.grey),
            ),
          ],
        ),
        trailing: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text(
              '\$${shipment.ourPrice.toStringAsFixed(2)}',
              style: TextStyle(
                fontWeight: FontWeight.bold,
                color: Colors.green,
              ),
            ),
            if (shipment.savings > 0)
              Text(
                'Saved \$${shipment.savings.toStringAsFixed(2)}',
                style: TextStyle(fontSize: 11, color: Colors.grey),
              ),
          ],
        ),
        children: [
          Padding(
            padding: EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'From:',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                Text('${shipment.fromAddress.city}, ${shipment.fromAddress.state}'),
                SizedBox(height: 8),
                Text(
                  'To:',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                Text('${shipment.toAddress.name}'),
                Text('${shipment.toAddress.street1}'),
                if (shipment.toAddress.street2 != null)
                  Text('${shipment.toAddress.street2}'),
                Text(
                  '${shipment.toAddress.city}, '
                  '${shipment.toAddress.state} '
                  '${shipment.toAddress.zip}'
                ),
                SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () {
                          // TODO: Track shipment
                        },
                        icon: Icon(Icons.location_on),
                        label: Text('Track'),
                      ),
                    ),
                    SizedBox(width: 8),
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () {
                          // TODO: View label
                        },
                        icon: Icon(Icons.receipt),
                        label: Text('View Label'),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
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
}
