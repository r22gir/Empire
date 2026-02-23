import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../providers/shipping_provider.dart';
import '../../models/shipment.dart';
import '../../widgets/shipping/address_form.dart';
import '../../widgets/shipping/package_dimensions.dart';
import 'rate_comparison_screen.dart';

class CreateShipmentScreen extends StatefulWidget {
  @override
  _CreateShipmentScreenState createState() => _CreateShipmentScreenState();
}

class _CreateShipmentScreenState extends State<CreateShipmentScreen> {
  int _currentStep = 0;
  
  Address? _fromAddress;
  Address? _toAddress;
  Parcel? _parcel;
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('New Shipment'),
        backgroundColor: Colors.orange,
      ),
      body: Stepper(
        currentStep: _currentStep,
        onStepContinue: _onStepContinue,
        onStepCancel: _onStepCancel,
        steps: [
          Step(
            title: Text('From Address'),
            content: AddressForm(
              initialAddress: _fromAddress,
              onSaved: (address) {
                setState(() => _fromAddress = address);
              },
            ),
            isActive: _currentStep >= 0,
          ),
          Step(
            title: Text('To Address'),
            content: AddressForm(
              initialAddress: _toAddress,
              onSaved: (address) {
                setState(() => _toAddress = address);
              },
            ),
            isActive: _currentStep >= 1,
          ),
          Step(
            title: Text('Package Details'),
            content: PackageDimensions(
              initialParcel: _parcel,
              onSaved: (parcel) {
                setState(() => _parcel = parcel);
              },
            ),
            isActive: _currentStep >= 2,
          ),
        ],
      ),
    );
  }
  
  void _onStepContinue() {
    if (_currentStep < 2) {
      setState(() => _currentStep++);
    } else {
      // All steps complete, fetch rates
      if (_fromAddress != null && _toAddress != null && _parcel != null) {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (context) => RateComparisonScreen(
              fromAddress: _fromAddress!,
              toAddress: _toAddress!,
              parcel: _parcel!,
            ),
          ),
        );
      }
    }
  }
  
  void _onStepCancel() {
    if (_currentStep > 0) {
      setState(() => _currentStep--);
    } else {
      Navigator.pop(context);
    }
  }
}
