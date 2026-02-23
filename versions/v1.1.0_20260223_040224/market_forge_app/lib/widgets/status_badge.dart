import 'package:flutter/material.dart';
import 'package:market_forge_app/models/listing.dart';

/// Status badge widget for listing status
class StatusBadge extends StatelessWidget {
  final ListingStatus status;
  final bool showIcon;

  const StatusBadge({
    super.key,
    required this.status,
    this.showIcon = true,
  });

  @override
  Widget build(BuildContext context) {
    final config = _getStatusConfig();
    
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: config.color.withOpacity(0.2),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: config.color, width: 1.5),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (showIcon) ...[
            Icon(
              config.icon,
              size: 16,
              color: config.color,
            ),
            const SizedBox(width: 6),
          ],
          Text(
            config.text,
            style: TextStyle(
              color: config.color,
              fontSize: 13,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }

  _StatusConfig _getStatusConfig() {
    switch (status) {
      case ListingStatus.posted:
        return _StatusConfig(
          color: Colors.green,
          text: 'Posted',
          icon: Icons.check_circle,
        );
      case ListingStatus.pending:
        return _StatusConfig(
          color: Colors.orange,
          text: 'Pending',
          icon: Icons.pending,
        );
      case ListingStatus.failed:
        return _StatusConfig(
          color: Colors.red,
          text: 'Failed',
          icon: Icons.error,
        );
      case ListingStatus.sold:
        return _StatusConfig(
          color: Colors.blue,
          text: 'Sold',
          icon: Icons.sell,
        );
      case ListingStatus.deleted:
        return _StatusConfig(
          color: Colors.grey,
          text: 'Deleted',
          icon: Icons.delete,
        );
    }
  }
}

class _StatusConfig {
  final Color color;
  final String text;
  final IconData icon;

  _StatusConfig({
    required this.color,
    required this.text,
    required this.icon,
  });
}
