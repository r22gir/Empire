import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:market_forge_app/screens/home_screen.dart';
import 'package:market_forge_app/screens/camera_screen.dart';
import 'package:market_forge_app/screens/settings_screen.dart';
import 'package:market_forge_app/screens/messages_screen.dart';
import 'package:market_forge_app/screens/email_settings_screen.dart';
import 'package:market_forge_app/providers/product_provider.dart';
import 'package:market_forge_app/providers/listing_provider.dart';
import 'package:market_forge_app/providers/user_provider.dart';
import 'package:market_forge_app/providers/message_provider.dart';

void main() {
  runApp(const MarketForgeApp());
}

class MarketForgeApp extends StatelessWidget {
  const MarketForgeApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => ProductProvider()),
        ChangeNotifierProvider(create: (_) => ListingProvider()),
        ChangeNotifierProvider(create: (_) => UserProvider()),
        ChangeNotifierProvider(create: (_) => MessageProvider(username: 'demo_user')),
      ],
      child: MaterialApp(
        title: 'MarketForge',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          useMaterial3: true,
          brightness: Brightness.dark,
          colorScheme: ColorScheme.dark(
            primary: Colors.deepPurple,
            secondary: Colors.deepPurpleAccent,
            surface: const Color(0xFF1E1E1E),
            background: const Color(0xFF121212),
            error: Colors.red,
          ),
          scaffoldBackgroundColor: const Color(0xFF121212),
          appBarTheme: const AppBarTheme(
            backgroundColor: Color(0xFF1E1E1E),
            elevation: 0,
          ),
          cardTheme: CardTheme(
            color: const Color(0xFF1E1E1E),
            elevation: 2,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
          ),
          elevatedButtonTheme: ElevatedButtonThemeData(
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.deepPurple,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(8),
              ),
            ),
          ),
          floatingActionButtonTheme: const FloatingActionButtonThemeData(
            backgroundColor: Colors.deepPurple,
            foregroundColor: Colors.white,
          ),
        ),
        home: const MainNavigationScreen(),
      ),
    );
  }
}

class MainNavigationScreen extends StatefulWidget {
  const MainNavigationScreen({super.key});

  @override
  State<MainNavigationScreen> createState() => _MainNavigationScreenState();
}

class _MainNavigationScreenState extends State<MainNavigationScreen> {
  int _currentIndex = 0;

  final List<Widget> _screens = [
    const HomeScreen(),
    const CameraScreen(),
    const MessagesScreen(),
    const SettingsScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _screens[_currentIndex],
      bottomNavigationBar: Consumer<MessageProvider>(
        builder: (context, messageProvider, child) {
          return NavigationBar(
            selectedIndex: _currentIndex,
            onDestinationSelected: (int index) {
              setState(() {
                _currentIndex = index;
              });
            },
            destinations: [
              const NavigationDestination(
                icon: Icon(Icons.home_outlined),
                selectedIcon: Icon(Icons.home),
                label: 'Home',
              ),
              const NavigationDestination(
                icon: Icon(Icons.add_a_photo_outlined),
                selectedIcon: Icon(Icons.add_a_photo),
                label: 'New Listing',
              ),
              NavigationDestination(
                icon: Badge(
                  label: Text('${messageProvider.unreadCount}'),
                  isLabelVisible: messageProvider.unreadCount > 0,
                  child: const Icon(Icons.chat_bubble_outline),
                ),
                selectedIcon: Badge(
                  label: Text('${messageProvider.unreadCount}'),
                  isLabelVisible: messageProvider.unreadCount > 0,
                  child: const Icon(Icons.chat_bubble),
                ),
                label: 'Messages',
              ),
              const NavigationDestination(
                icon: Icon(Icons.settings_outlined),
                selectedIcon: Icon(Icons.settings),
                label: 'Settings',
              ),
            ],
          );
        },
      ),
    );
  }
}