import 'package:flutter/material.dart';
import '../../models/shipment.dart';

class PackageDimensions extends StatefulWidget {
  final Parcel? initialParcel;
  final Function(Parcel) onSaved;
  
  PackageDimensions({this.initialParcel, required this.onSaved});
  
  @override
  _PackageDimensionsState createState() => _PackageDimensionsState();
}

class _PackageDimensionsState extends State<PackageDimensions> {
  final _formKey = GlobalKey<FormState>();
  String _selectedPreset = 'custom';
  late TextEditingController _lengthController;
  late TextEditingController _widthController;
  late TextEditingController _heightController;
  late TextEditingController _weightController;
  
  final Map<String, Map<String, double>> _presets = {
    'envelope': {'length': 12, 'width': 9, 'height': 0.25, 'weight': 4},
    'small_box': {'length': 8, 'width': 6, 'height': 4, 'weight': 16},
    'medium_box': {'length': 12, 'width': 10, 'height': 8, 'weight': 32},
    'large_box': {'length': 18, 'width': 14, 'height': 12, 'weight': 64},
  };
  
  @override
  void initState() {
    super.initState();
    _lengthController = TextEditingController(
      text: widget.initialParcel?.length.toString() ?? ''
    );
    _widthController = TextEditingController(
      text: widget.initialParcel?.width.toString() ?? ''
    );
    _heightController = TextEditingController(
      text: widget.initialParcel?.height.toString() ?? ''
    );
    _weightController = TextEditingController(
      text: widget.initialParcel?.weight.toString() ?? ''
    );
  }
  
  @override
  void dispose() {
    _lengthController.dispose();
    _widthController.dispose();
    _heightController.dispose();
    _weightController.dispose();
    super.dispose();
  }
  
  @override
  Widget build(BuildContext context) {
    return Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Package Presets',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
          ),
          SizedBox(height: 8),
          Wrap(
            spacing: 8,
            children: [
              _buildPresetChip('Envelope', 'envelope'),
              _buildPresetChip('Small Box', 'small_box'),
              _buildPresetChip('Medium Box', 'medium_box'),
              _buildPresetChip('Large Box', 'large_box'),
              _buildPresetChip('Custom', 'custom'),
            ],
          ),
          SizedBox(height: 16),
          Text(
            'Dimensions (inches)',
            style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
          ),
          Row(
            children: [
              Expanded(
                child: TextFormField(
                  controller: _lengthController,
                  decoration: InputDecoration(labelText: 'Length'),
                  keyboardType: TextInputType.numberWithOptions(decimal: true),
                  validator: (value) => _validateNumber(value),
                ),
              ),
              SizedBox(width: 8),
              Expanded(
                child: TextFormField(
                  controller: _widthController,
                  decoration: InputDecoration(labelText: 'Width'),
                  keyboardType: TextInputType.numberWithOptions(decimal: true),
                  validator: (value) => _validateNumber(value),
                ),
              ),
              SizedBox(width: 8),
              Expanded(
                child: TextFormField(
                  controller: _heightController,
                  decoration: InputDecoration(labelText: 'Height'),
                  keyboardType: TextInputType.numberWithOptions(decimal: true),
                  validator: (value) => _validateNumber(value),
                ),
              ),
            ],
          ),
          SizedBox(height: 16),
          TextFormField(
            controller: _weightController,
            decoration: InputDecoration(
              labelText: 'Weight (oz)',
              helperText: '16 oz = 1 lb',
            ),
            keyboardType: TextInputType.numberWithOptions(decimal: true),
            validator: (value) => _validateNumber(value),
          ),
          SizedBox(height: 16),
          ElevatedButton(
            onPressed: _saveParcel,
            child: Text('Save Package Details'),
          ),
        ],
      ),
    );
  }
  
  Widget _buildPresetChip(String label, String value) {
    return ChoiceChip(
      label: Text(label),
      selected: _selectedPreset == value,
      onSelected: (selected) {
        if (selected) {
          setState(() {
            _selectedPreset = value;
            if (value != 'custom') {
              final preset = _presets[value]!;
              _lengthController.text = preset['length'].toString();
              _widthController.text = preset['width'].toString();
              _heightController.text = preset['height'].toString();
              _weightController.text = preset['weight'].toString();
            }
          });
        }
      },
    );
  }
  
  String? _validateNumber(String? value) {
    if (value?.isEmpty ?? true) return 'Required';
    if (double.tryParse(value!) == null) return 'Invalid number';
    if (double.parse(value) <= 0) return 'Must be > 0';
    return null;
  }
  
  void _saveParcel() {
    if (_formKey.currentState?.validate() ?? false) {
      final parcel = Parcel(
        length: double.parse(_lengthController.text),
        width: double.parse(_widthController.text),
        height: double.parse(_heightController.text),
        weight: double.parse(_weightController.text),
      );
      widget.onSaved(parcel);
    }
  }
}
