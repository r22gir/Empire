import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:market_forge_app/providers/product_provider.dart';
import 'package:market_forge_app/providers/listing_provider.dart';
import 'package:market_forge_app/widgets/photo_thumbnail.dart';
import 'package:market_forge_app/screens/product_form_screen.dart';

/// Camera screen for capturing photos
class CameraScreen extends StatefulWidget {
  const CameraScreen({super.key});

  @override
  State<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen> {
  final List<String> _photoUrls = [];
  final int _maxPhotos = 10;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Take Photos'),
        actions: [
          if (_photoUrls.isNotEmpty)
            TextButton(
              onPressed: _clearAll,
              child: const Text('Clear All'),
            ),
        ],
      ),
      body: Column(
        children: [
          // Camera preview placeholder
          Expanded(
            child: _buildCameraPreview(),
          ),
          
          // Photo thumbnails
          if (_photoUrls.isNotEmpty)
            Container(
              height: 120,
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: ListView.builder(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 16),
                itemCount: _photoUrls.length,
                itemBuilder: (context, index) {
                  return Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: SizedBox(
                      width: 100,
                      child: PhotoThumbnail(
                        photoPath: _photoUrls[index],
                        onDelete: () => _removePhoto(index),
                      ),
                    ),
                  );
                },
              ),
            ),
          
          // Controls
          Container(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                  children: [
                    // Gallery button
                    Column(
                      children: [
                        IconButton(
                          icon: const Icon(Icons.photo_library),
                          iconSize: 32,
                          onPressed: _pickFromGallery,
                        ),
                        const Text('Gallery', style: TextStyle(fontSize: 12)),
                      ],
                    ),
                    
                    // Capture button
                    Column(
                      children: [
                        Container(
                          width: 70,
                          height: 70,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            border: Border.all(color: Colors.white, width: 4),
                          ),
                          child: Material(
                            color: Colors.deepPurple,
                            shape: const CircleBorder(),
                            child: InkWell(
                              onTap: _photoUrls.length < _maxPhotos
                                  ? _capturePhoto
                                  : null,
                              customBorder: const CircleBorder(),
                              child: const Icon(
                                Icons.camera_alt,
                                size: 32,
                                color: Colors.white,
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          '${_photoUrls.length}/$_maxPhotos',
                          style: const TextStyle(fontSize: 12),
                        ),
                      ],
                    ),
                    
                    // Flash button
                    Column(
                      children: [
                        IconButton(
                          icon: const Icon(Icons.flash_off),
                          iconSize: 32,
                          onPressed: () {
                            // TODO: Toggle flash
                          },
                        ),
                        const Text('Flash', style: TextStyle(fontSize: 12)),
                      ],
                    ),
                  ],
                ),
                
                const SizedBox(height: 16),
                
                // Continue button
                if (_photoUrls.isNotEmpty)
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: _continue,
                      style: ElevatedButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 16),
                      ),
                      child: const Text(
                        'Continue to Product Details',
                        style: TextStyle(fontSize: 16),
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCameraPreview() {
    return Container(
      color: Colors.black,
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.camera_alt_outlined,
              size: 80,
              color: Colors.grey[700],
            ),
            const SizedBox(height: 16),
            Text(
              'Camera Preview',
              style: TextStyle(
                color: Colors.grey[700],
                fontSize: 18,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Tap the capture button to take a photo',
              style: TextStyle(
                color: Colors.grey[700],
                fontSize: 14,
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _capturePhoto() {
    if (_photoUrls.length >= _maxPhotos) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Maximum $_maxPhotos photos allowed'),
          backgroundColor: Colors.orange,
        ),
      );
      return;
    }

    setState(() {
      // Mock photo URL - in real implementation, this would be the captured photo path
      _photoUrls.add('https://via.placeholder.com/400x400?text=Photo+${_photoUrls.length + 1}');
    });
  }

  void _pickFromGallery() async {
    if (_photoUrls.length >= _maxPhotos) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Maximum $_maxPhotos photos allowed'),
          backgroundColor: Colors.orange,
        ),
      );
      return;
    }

    // TODO: Implement image picker
    // For now, add mock photo
    setState(() {
      _photoUrls.add('https://via.placeholder.com/400x400?text=Gallery+Photo');
    });
  }

  void _removePhoto(int index) {
    setState(() {
      _photoUrls.removeAt(index);
    });
  }

  void _clearAll() {
    setState(() {
      _photoUrls.clear();
    });
  }

  void _continue() {
    final productProvider = context.read<ProductProvider>();
    final listingProvider = context.read<ListingProvider>();
    
    // Create a new draft product
    final product = productProvider.createDraft(
      photoUrls: List.from(_photoUrls),
    );
    
    // Start listing flow
    listingProvider.startNewListing(product);
    
    // Navigate to product form
    Navigator.pushReplacement(
      context,
      MaterialPageRoute(
        builder: (context) => const ProductFormScreen(),
      ),
    );
  }
}
