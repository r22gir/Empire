import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:market_forge_app/providers/listing_provider.dart';
import 'package:market_forge_app/models/product.dart';
import 'package:market_forge_app/services/ai_service.dart';
import 'package:market_forge_app/screens/marketplace_picker_screen.dart';
import 'package:intl/intl.dart';

/// Product form screen for entering product details
class ProductFormScreen extends StatefulWidget {
  const ProductFormScreen({super.key});

  @override
  State<ProductFormScreen> createState() => _ProductFormScreenState();
}

class _ProductFormScreenState extends State<ProductFormScreen> {
  final _formKey = GlobalKey<FormState>();
  final _titleController = TextEditingController();
  final _priceController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _locationController = TextEditingController();
  
  String _selectedCategory = ProductCategory.electronics;
  String _selectedCondition = ProductCondition.good;
  bool _isLoadingAi = false;
  final _aiService = AiService();

  @override
  void initState() {
    super.initState();
    _autoDetectLocation();
  }

  @override
  void dispose() {
    _titleController.dispose();
    _priceController.dispose();
    _descriptionController.dispose();
    _locationController.dispose();
    super.dispose();
  }

  void _autoDetectLocation() {
    // TODO: Implement actual location detection
    _locationController.text = 'San Francisco, CA';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Product Details'),
      ),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // Title field
            TextFormField(
              controller: _titleController,
              decoration: InputDecoration(
                labelText: 'Title *',
                hintText: 'e.g., Nike Air Max Size 10',
                border: const OutlineInputBorder(),
                suffixIcon: IconButton(
                  icon: const Icon(Icons.auto_awesome),
                  onPressed: _generateTitleSuggestions,
                  tooltip: 'AI Suggestions',
                ),
              ),
              maxLength: 100,
              validator: (value) {
                if (value == null || value.isEmpty) {
                  return 'Title is required';
                }
                return null;
              },
            ),
            
            const SizedBox(height: 16),
            
            // Price field
            TextFormField(
              controller: _priceController,
              decoration: const InputDecoration(
                labelText: 'Price *',
                hintText: '0.00',
                border: OutlineInputBorder(),
                prefixText: '\$ ',
              ),
              keyboardType: TextInputType.numberWithOptions(decimal: true),
              validator: (value) {
                if (value == null || value.isEmpty) {
                  return 'Price is required';
                }
                final price = double.tryParse(value);
                if (price == null || price <= 0) {
                  return 'Enter a valid price';
                }
                return null;
              },
            ),
            
            const SizedBox(height: 16),
            
            // Category dropdown
            DropdownButtonFormField<String>(
              value: _selectedCategory,
              decoration: const InputDecoration(
                labelText: 'Category *',
                border: OutlineInputBorder(),
              ),
              items: ProductCategory.all.map((category) {
                return DropdownMenuItem(
                  value: category,
                  child: Text(category),
                );
              }).toList(),
              onChanged: (value) {
                setState(() {
                  _selectedCategory = value!;
                });
              },
            ),
            
            const SizedBox(height: 16),
            
            // Condition picker
            DropdownButtonFormField<String>(
              value: _selectedCondition,
              decoration: const InputDecoration(
                labelText: 'Condition *',
                border: OutlineInputBorder(),
              ),
              items: ProductCondition.all.map((condition) {
                return DropdownMenuItem(
                  value: condition,
                  child: Text(condition),
                );
              }).toList(),
              onChanged: (value) {
                setState(() {
                  _selectedCondition = value!;
                });
              },
            ),
            
            const SizedBox(height: 16),
            
            // Description field
            TextFormField(
              controller: _descriptionController,
              decoration: InputDecoration(
                labelText: 'Description *',
                hintText: 'Describe your product...',
                border: const OutlineInputBorder(),
                alignLabelWithHint: true,
                suffixIcon: IconButton(
                  icon: const Icon(Icons.auto_fix_high),
                  onPressed: _enhanceDescription,
                  tooltip: 'AI Enhance',
                ),
              ),
              maxLines: 5,
              maxLength: 5000,
              validator: (value) {
                if (value == null || value.isEmpty) {
                  return 'Description is required';
                }
                return null;
              },
            ),
            
            const SizedBox(height: 16),
            
            // Location field
            TextFormField(
              controller: _locationController,
              decoration: InputDecoration(
                labelText: 'Location *',
                hintText: 'City, State',
                border: const OutlineInputBorder(),
                suffixIcon: IconButton(
                  icon: const Icon(Icons.my_location),
                  onPressed: _autoDetectLocation,
                  tooltip: 'Auto-detect',
                ),
              ),
              validator: (value) {
                if (value == null || value.isEmpty) {
                  return 'Location is required';
                }
                return null;
              },
            ),
            
            const SizedBox(height: 24),
            
            // Continue button
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _isLoadingAi ? null : _continue,
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                ),
                child: const Text(
                  'Continue to Marketplaces',
                  style: TextStyle(fontSize: 16),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _generateTitleSuggestions() async {
    final listingProvider = context.read<ListingProvider>();
    final product = listingProvider.currentProduct;
    
    if (product == null || product.photoUrls.isEmpty) {
      _showSnackBar('Add photos first to get AI suggestions');
      return;
    }

    setState(() {
      _isLoadingAi = true;
    });

    try {
      final suggestions = await _aiService.generateTitleSuggestions(
        photoUrls: product.photoUrls,
        category: _selectedCategory,
      );

      if (suggestions.isNotEmpty && mounted) {
        _showSuggestionsDialog('Title Suggestions', suggestions, (selected) {
          _titleController.text = selected;
        });
      } else {
        _showSnackBar('No suggestions available');
      }
    } catch (e) {
      _showSnackBar('Error getting suggestions: $e');
    } finally {
      setState(() {
        _isLoadingAi = false;
      });
    }
  }

  Future<void> _enhanceDescription() async {
    if (_titleController.text.isEmpty || _descriptionController.text.isEmpty) {
      _showSnackBar('Enter title and description first');
      return;
    }

    setState(() {
      _isLoadingAi = true;
    });

    try {
      final enhanced = await _aiService.enhanceDescription(
        originalDescription: _descriptionController.text,
        title: _titleController.text,
        category: _selectedCategory,
      );

      if (enhanced != null && mounted) {
        _showEnhancementDialog(enhanced);
      } else {
        _showSnackBar('No enhancement available');
      }
    } catch (e) {
      _showSnackBar('Error enhancing description: $e');
    } finally {
      setState(() {
        _isLoadingAi = false;
      });
    }
  }

  void _showSuggestionsDialog(
    String title,
    List<String> suggestions,
    Function(String) onSelect,
  ) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: suggestions.map((suggestion) {
              return ListTile(
                title: Text(suggestion),
                onTap: () {
                  onSelect(suggestion);
                  Navigator.pop(context);
                },
              );
            }).toList(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
        ],
      ),
    );
  }

  void _showEnhancementDialog(String enhanced) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Enhanced Description'),
        content: SingleChildScrollView(
          child: Text(enhanced),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              _descriptionController.text = enhanced;
              Navigator.pop(context);
            },
            child: const Text('Use This'),
          ),
        ],
      ),
    );
  }

  void _showSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  void _continue() {
    if (!_formKey.currentState!.validate()) {
      return;
    }

    final listingProvider = context.read<ListingProvider>();
    final currentProduct = listingProvider.currentProduct;
    
    if (currentProduct == null) {
      _showSnackBar('Error: No product found');
      return;
    }

    // Update product with form data
    final updatedProduct = currentProduct.copyWith(
      title: _titleController.text,
      price: double.parse(_priceController.text),
      category: _selectedCategory,
      condition: _selectedCondition,
      description: _descriptionController.text,
      location: _locationController.text,
    );

    listingProvider.updateCurrentProduct(updatedProduct);

    // Navigate to marketplace picker
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => const MarketplacePickerScreen(),
      ),
    );
  }
}
