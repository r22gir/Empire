import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../providers/shipping_provider.dart';
import '../../models/shipment.dart';
import '../../widgets/shipping/rate_card.dart';
import 'label_preview_screen.dart';

class RateComparisonScreen extends StatefulWidget {
  final Address fromAddress;
  final Address toAddress;
  final Parcel parcel;
  
  RateComparisonScreen({
    required this.fromAddress,
    required this.toAddress,
    required this.parcel,
  });
  
  @override
  _RateComparisonScreenState createState() => _RateComparisonScreenState();
}

class _RateComparisonScreenState extends State<RateComparisonScreen> {
  List<ShippingRate>? _rates;
  bool _isLoading = true;
  String? _error;
  String _sortBy = 'price'; // 'price' or 'speed'
  
  @override
  void initState() {
    super.initState();
    _fetchRates();
  }
  
  Future<void> _fetchRates() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    
    try {
      final provider = Provider.of<ShippingProvider>(context, listen: false);
      final rates = await provider.getRates(
        fromAddress: widget.fromAddress,
        toAddress: widget.toAddress,
        parcel: widget.parcel,
      );
      
      setState(() {
        _rates = rates;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }
  
  List<ShippingRate> _getSortedRates() {
    if (_rates == null) return [];
    
    final sorted = List<ShippingRate>.from(_rates!);
    
    if (_sortBy == 'price') {
      sorted.sort((a, b) => a.ourPrice.compareTo(b.ourPrice));
    } else {
      sorted.sort((a, b) {
        final aDays = a.deliveryDays ?? 999;
        final bDays = b.deliveryDays ?? 999;
        return aDays.compareTo(bDays);
      });
    }
    
    return sorted;
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Compare Rates'),
        backgroundColor: Colors.orange,
        actions: [
          PopupMenuButton<String>(
            onSelected: (value) {
              setState(() => _sortBy = value);
            },
            itemBuilder: (context) => [
              PopupMenuItem(
                value: 'price',
                child: Text('Sort by Price'),
              ),
              PopupMenuItem(
                value: 'speed',
                child: Text('Sort by Speed'),
              ),
            ],
          ),
        ],
      ),
      body: _buildBody(),
    );
  }
  
  Widget _buildBody() {
    if (_isLoading) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text('Fetching shipping rates...'),
          ],
        ),
      );
    }
    
    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.error_outline, size: 64, color: Colors.red),
            SizedBox(height: 16),
            Text('Failed to load rates'),
            SizedBox(height: 8),
            Text(_error!, style: TextStyle(color: Colors.grey)),
            SizedBox(height: 16),
            ElevatedButton(
              onPressed: _fetchRates,
              child: Text('Retry'),
            ),
          ],
        ),
      );
    }
    
    final sortedRates = _getSortedRates();
    
    if (sortedRates.isEmpty) {
      return Center(
        child: Text('No rates available'),
      );
    }
    
    return ListView.builder(
      padding: EdgeInsets.all(16),
      itemCount: sortedRates.length,
      itemBuilder: (context, index) {
        final rate = sortedRates[index];
        final isCheapest = index == 0 && _sortBy == 'price';
        final isFastest = index == 0 && _sortBy == 'speed';
        
        return RateCard(
          rate: rate,
          isCheapest: isCheapest,
          isFastest: isFastest,
          onSelect: () => _selectRate(rate),
        );
      },
    );
  }
  
  Future<void> _selectRate(ShippingRate rate) async {
    // Show loading dialog
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => Center(
        child: Card(
          child: Padding(
            padding: EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                CircularProgressIndicator(),
                SizedBox(height: 16),
                Text('Purchasing label...'),
              ],
            ),
          ),
        ),
      ),
    );
    
    try {
      final provider = Provider.of<ShippingProvider>(context, listen: false);
      final shipment = await provider.purchaseLabel(
        shipmentId: rate.shipmentId,
        rateId: rate.rateId,
      );
      
      // Close loading dialog
      Navigator.pop(context);
      
      // Navigate to label preview
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (context) => LabelPreviewScreen(shipment: shipment),
        ),
      );
    } catch (e) {
      // Close loading dialog
      Navigator.pop(context);
      
      // Show error
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to purchase label: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }
}
