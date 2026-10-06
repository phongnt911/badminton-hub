import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'core/app_constants.dart';
import 'screens/home_screen.dart';
import 'screens/venues_screen.dart';
import 'screens/tools_screen.dart';
import 'screens/clubs_screen.dart';

import 'package:provider/provider.dart';
import 'package:badminton_hub/providers/club_provider.dart';
import 'package:badminton_hub/providers/session_provider.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Khởi tạo Supabase với thông số của bạn
  await Supabase.initialize(
    url: AppConstants.supabaseUrl,
    publishableKey: AppConstants.supabaseAnonKey,
  );

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => ClubProvider()),
        ChangeNotifierProvider(create: (_) => SessionProvider()),
      ],
      child: const BadmintonHubApp(),
    ),
  );
}

class BadmintonHubApp extends StatelessWidget {
  const BadmintonHubApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Badminton Nha Trang Hub',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: AppConstants.primaryColor),
        useMaterial3: true,
      ),
      home: const MainNavigationScreen(),
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

  final List<Widget> _screens = const [
    HomeScreen(),
    VenuesScreen(),
    ClubsScreen(),
    ToolsScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _screens[_currentIndex],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        onDestinationSelected: (idx) => setState(() => _currentIndex = idx),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.sports_tennis),
            label: 'Kèo Hôm Nay',
          ),
          NavigationDestination(
            icon: Icon(Icons.location_on),
            label: 'Sân Nha Trang',
          ),
          NavigationDestination(
            icon: Icon(Icons.group),
            label: 'CLB & Quỹ',
          ),
          NavigationDestination(icon: Icon(Icons.build), label: 'Tiện Ích'),
        ],
      ),
    );
  }
}
