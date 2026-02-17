import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'providers/shipping_provider.dart';
import 'screens/shipping_screen.dart';
import 'services/deep_link_service.dart';

void main() {
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => ShippingProvider()),
      ],
      child: MaterialApp(
        title: 'MarketForge',
        theme: ThemeData(
          primarySwatch: Colors.blue,
          colorScheme: ColorScheme.fromSeed(
            seedColor: Color(0xFF1E40AF),
            secondary: Color(0xFFF97316),
          ),
        ),
        home: MainScreen(),
      ),
    );
  }
}

class MainScreen extends StatefulWidget {
  @override
  _MainScreenState createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  int _selectedIndex = 0;
  final DeepLinkService _deepLinkService = DeepLinkService();
  
  final List<Widget> _screens = [
    HomeScreen(),
    ShippingScreen(),
    ProfileScreen(),
  ];
  
  @override
  void initState() {
    super.initState();
    _deepLinkService.init((uri) {
      _deepLinkService.handleDeepLink(uri, (licenseKey) {
        // Navigate to activation screen
        _showActivationDialog(licenseKey);
      });
    });
  }
  
  @override
  void dispose() {
    _deepLinkService.dispose();
    super.dispose();
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _screens[_selectedIndex],
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _selectedIndex,
        onTap: (index) {
          setState(() => _selectedIndex = index);
        },
        items: [
          BottomNavigationBarItem(
            icon: Icon(Icons.home),
            label: 'Home',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.local_shipping),
            label: 'Shipping',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.person),
            label: 'Profile',
          ),
        ],
      ),
    );
  }
  
  void _showActivationDialog(String licenseKey) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Activate License'),
        content: Text('License Key: $licenseKey\n\nWould you like to activate this license?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              // TODO: Implement license activation
              Navigator.pop(context);
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('License activated!')),
              );
            },
            child: Text('Activate'),
          ),
        ],
      ),
    );
  }
}

class HomeScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('MarketForge'),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.storefront, size: 100, color: Colors.blue),
            SizedBox(height: 16),
            Text(
              'MarketForge',
              style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold),
            ),
            SizedBox(height: 8),
            Text(
              'Your AI-powered reselling platform',
              style: TextStyle(fontSize: 16, color: Colors.grey),
            ),
          ],
        ),
      ),
    );
  }
}

class ProfileScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Profile'),
      ),
      body: Center(
        child: Text('Profile Screen'),
      ),
    );
  }
}
