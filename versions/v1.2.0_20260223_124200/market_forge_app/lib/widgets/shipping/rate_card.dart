import 'package:flutter/material.dart';
import '../../models/shipment.dart';

class RateCard extends StatelessWidget {
  final ShippingRate rate;
  final bool isCheapest;
  final bool isFastest;
  final VoidCallback onSelect;
  
  RateCard({
    required this.rate,
    this.isCheapest = false,
    this.isFastest = false,
    required this.onSelect,
  });
  
  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: isCheapest || isFastest ? 4 : 2,
      margin: EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(
          color: isCheapest || isFastest ? Colors.orange : Colors.transparent,
          width: 2,
        ),
      ),
      child: InkWell(
        onTap: onSelect,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  _getCarrierIcon(),
                  SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '${rate.carrier} ${rate.service}',
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        if (rate.deliveryDays != null)
                          Text(
                            'Delivery: ${rate.deliveryDays} ${rate.deliveryDays == 1 ? "day" : "days"}',
                            style: TextStyle(color: Colors.grey, fontSize: 14),
                          ),
                      ],
                    ),
                  ),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text(
                        '\$${rate.ourPrice.toStringAsFixed(2)}',
                        style: TextStyle(
                          fontSize: 24,
                          fontWeight: FontWeight.bold,
                          color: Colors.green,
                        ),
                      ),
                      if (rate.savings > 0)
                        Text(
                          'Save \$${rate.savings.toStringAsFixed(2)}!',
                          style: TextStyle(
                            fontSize: 12,
                            color: Colors.orange,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                    ],
                  ),
                ],
              ),
              if (isCheapest || isFastest) ...[
                SizedBox(height: 8),
                Container(
                  padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.orange.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    isCheapest ? '🏆 CHEAPEST OPTION' : '⚡ FASTEST OPTION',
                    style: TextStyle(
                      color: Colors.orange,
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
  
  Widget _getCarrierIcon() {
    IconData icon;
    Color color;
    
    switch (rate.carrier.toUpperCase()) {
      case 'USPS':
        icon = Icons.mail;
        color = Colors.blue;
        break;
      case 'UPS':
        icon = Icons.local_shipping;
        color = Colors.brown;
        break;
      case 'FEDEX':
        icon = Icons.flight;
        color = Colors.purple;
        break;
      default:
        icon = Icons.local_shipping;
        color = Colors.grey;
    }
    
    return CircleAvatar(
      backgroundColor: color.withOpacity(0.1),
      child: Icon(icon, color: color),
    );
  }
}
