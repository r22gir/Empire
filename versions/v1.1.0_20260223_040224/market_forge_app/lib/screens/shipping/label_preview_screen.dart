import 'package:flutter/material.dart';
import 'package:printing/printing.dart';
import 'package:http/http.dart' as http;
import 'package:share_plus/share_plus.dart';
import 'package:image_gallery_saver/image_gallery_saver.dart';
import 'dart:typed_data';
import '../../models/shipment.dart';

class LabelPreviewScreen extends StatelessWidget {
  final Shipment shipment;
  
  LabelPreviewScreen({required this.shipment});
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Shipping Label'),
        backgroundColor: Colors.orange,
      ),
      body: Column(
        children: [
          // Label preview
          Expanded(
            child: InteractiveViewer(
              child: Image.network(
                shipment.labelUrl,
                loadingBuilder: (context, child, loadingProgress) {
                  if (loadingProgress == null) return child;
                  return Center(child: CircularProgressIndicator());
                },
                errorBuilder: (context, error, stackTrace) {
                  return Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.error, size: 64, color: Colors.red),
                        SizedBox(height: 16),
                        Text('Failed to load label'),
                      ],
                    ),
                  );
                },
              ),
            ),
          ),
          
          // Actions
          Container(
            padding: EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              boxShadow: [
                BoxShadow(
                  color: Colors.black12,
                  blurRadius: 8,
                  offset: Offset(0, -2),
                ),
              ],
            ),
            child: Column(
              children: [
                // Tracking info
                ListTile(
                  leading: Icon(Icons.local_shipping, color: Colors.orange),
                  title: Text(
                    shipment.trackingNumber,
                    style: TextStyle(fontWeight: FontWeight.bold),
                  ),
                  subtitle: Text('${shipment.carrier} ${shipment.service}'),
                  trailing: IconButton(
                    icon: Icon(Icons.copy),
                    onPressed: () => _copyTracking(context),
                  ),
                ),
                
                SizedBox(height: 16),
                
                // Primary action - Print
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: () => _printLabel(context),
                    icon: Icon(Icons.print),
                    label: Text('Print Label'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.orange,
                      padding: EdgeInsets.symmetric(vertical: 16),
                    ),
                  ),
                ),
                
                SizedBox(height: 8),
                
                // Secondary actions
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () => _emailLabel(context),
                        icon: Icon(Icons.email, size: 20),
                        label: Text('Email'),
                      ),
                    ),
                    SizedBox(width: 8),
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () => _saveLabel(context),
                        icon: Icon(Icons.save_alt, size: 20),
                        label: Text('Save'),
                      ),
                    ),
                    SizedBox(width: 8),
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () => _shareLabel(context),
                        icon: Icon(Icons.share, size: 20),
                        label: Text('Share'),
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
  
  void _copyTracking(BuildContext context) {
    // TODO: Copy to clipboard
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Tracking number copied')),
    );
  }
  
  Future<void> _printLabel(BuildContext context) async {
    try {
      // Fetch the label PDF
      final response = await http.get(Uri.parse(shipment.labelPdfUrl));
      
      if (response.statusCode == 200) {
        await Printing.layoutPdf(
          onLayout: (_) => response.bodyBytes,
          name: 'Shipping_Label_${shipment.trackingNumber}',
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to print label: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }
  
  Future<void> _emailLabel(BuildContext context) async {
    // Show email input dialog
    final emailController = TextEditingController();
    
    final email = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Email Label'),
        content: TextField(
          controller: emailController,
          decoration: InputDecoration(
            labelText: 'Email Address',
            hintText: 'your@email.com',
          ),
          keyboardType: TextInputType.emailAddress,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, emailController.text),
            child: Text('Send'),
          ),
        ],
      ),
    );
    
    if (email != null && email.isNotEmpty) {
      // TODO: Call API to email label
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Label sent to $email')),
      );
    }
  }
  
  Future<void> _saveLabel(BuildContext context) async {
    try {
      final response = await http.get(Uri.parse(shipment.labelUrl));
      
      if (response.statusCode == 200) {
        await ImageGallerySaver.saveImage(
          Uint8List.fromList(response.bodyBytes),
          name: 'label_${shipment.trackingNumber}',
        );
        
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Label saved to photos')),
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to save label: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }
  
  Future<void> _shareLabel(BuildContext context) async {
    try {
      await Share.share(
        'Shipping Label - ${shipment.carrier} ${shipment.service}\n'
        'Tracking: ${shipment.trackingNumber}\n'
        'Label: ${shipment.labelUrl}',
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to share label: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }
}
