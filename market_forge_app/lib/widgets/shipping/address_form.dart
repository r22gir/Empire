import 'package:flutter/material.dart';
import '../../models/shipment.dart';

class AddressForm extends StatefulWidget {
  final Address? initialAddress;
  final Function(Address) onSaved;
  
  AddressForm({this.initialAddress, required this.onSaved});
  
  @override
  _AddressFormState createState() => _AddressFormState();
}

class _AddressFormState extends State<AddressForm> {
  final _formKey = GlobalKey<FormState>();
  late TextEditingController _nameController;
  late TextEditingController _street1Controller;
  late TextEditingController _street2Controller;
  late TextEditingController _cityController;
  late TextEditingController _stateController;
  late TextEditingController _zipController;
  
  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController(text: widget.initialAddress?.name ?? '');
    _street1Controller = TextEditingController(text: widget.initialAddress?.street1 ?? '');
    _street2Controller = TextEditingController(text: widget.initialAddress?.street2 ?? '');
    _cityController = TextEditingController(text: widget.initialAddress?.city ?? '');
    _stateController = TextEditingController(text: widget.initialAddress?.state ?? '');
    _zipController = TextEditingController(text: widget.initialAddress?.zip ?? '');
  }
  
  @override
  void dispose() {
    _nameController.dispose();
    _street1Controller.dispose();
    _street2Controller.dispose();
    _cityController.dispose();
    _stateController.dispose();
    _zipController.dispose();
    super.dispose();
  }
  
  @override
  Widget build(BuildContext context) {
    return Form(
      key: _formKey,
      child: Column(
        children: [
          TextFormField(
            controller: _nameController,
            decoration: InputDecoration(labelText: 'Name *'),
            validator: (value) => value?.isEmpty ?? true ? 'Required' : null,
          ),
          TextFormField(
            controller: _street1Controller,
            decoration: InputDecoration(labelText: 'Street Address *'),
            validator: (value) => value?.isEmpty ?? true ? 'Required' : null,
          ),
          TextFormField(
            controller: _street2Controller,
            decoration: InputDecoration(labelText: 'Apt, Suite, etc.'),
          ),
          Row(
            children: [
              Expanded(
                flex: 2,
                child: TextFormField(
                  controller: _cityController,
                  decoration: InputDecoration(labelText: 'City *'),
                  validator: (value) => value?.isEmpty ?? true ? 'Required' : null,
                ),
              ),
              SizedBox(width: 8),
              Expanded(
                child: TextFormField(
                  controller: _stateController,
                  decoration: InputDecoration(labelText: 'State *'),
                  maxLength: 2,
                  validator: (value) => value?.isEmpty ?? true ? 'Required' : null,
                ),
              ),
            ],
          ),
          TextFormField(
            controller: _zipController,
            decoration: InputDecoration(labelText: 'ZIP Code *'),
            keyboardType: TextInputType.number,
            maxLength: 5,
            validator: (value) => value?.isEmpty ?? true ? 'Required' : null,
          ),
          SizedBox(height: 16),
          ElevatedButton(
            onPressed: _saveAddress,
            child: Text('Save Address'),
          ),
        ],
      ),
    );
  }
  
  void _saveAddress() {
    if (_formKey.currentState?.validate() ?? false) {
      final address = Address(
        name: _nameController.text,
        street1: _street1Controller.text,
        street2: _street2Controller.text.isEmpty ? null : _street2Controller.text,
        city: _cityController.text,
        state: _stateController.text.toUpperCase(),
        zip: _zipController.text,
      );
      widget.onSaved(address);
    }
  }
}
