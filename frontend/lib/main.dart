import "package:flutter/material.dart";

import "package:expenis_mobile/screens/account_screen.dart";
import "package:expenis_mobile/screens/category_screen.dart";
import "package:expenis_mobile/screens/change_password_screen.dart";
import "package:expenis_mobile/screens/login_screen.dart";
import "package:expenis_mobile/screens/register_screen.dart";
import "package:expenis_mobile/screens/settings_screen.dart";
import "package:expenis_mobile/screens/transaction_screen.dart";
import "package:expenis_mobile/screens/transaction_stats_screen.dart";
import "package:expenis_mobile/service/navigator_service.dart";
import "package:expenis_mobile/service/settings_service.dart";
import "package:expenis_mobile/theme.dart";

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: "My Pennies",
      theme: AppTheme.light,
      navigatorKey: appNavigatorKey,
      initialRoute: "/boot",
      routes: {
        "/boot": (_) => const _AuthGate(),
        "/login": (_) => const LoginScreen(),
        "/register": (_) => const RegisterScreen(),
        "/home": (_) => const HomeScreen(),
        "/settings": (_) => const SettingsScreen(),
        "/change-password": (_) => const ChangePasswordScreen(),
      },
    );
  }
}

class _AuthGate extends StatefulWidget {
  const _AuthGate();

  @override
  State<_AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<_AuthGate> {
  @override
  void initState() {
    super.initState();
    _decide();
  }

  Future<void> _decide() async {
    final settingsService = await SettingsService.getInstance();
    final hasToken = await settingsService.hasAccessToken();
    final routeName = hasToken ? "/home" : "/login";
    if (!mounted) return;
    Navigator.of(context).pushReplacementNamed(routeName);
  }

  @override
  Widget build(BuildContext context) {
    return const Scaffold(body: Center(child: CircularProgressIndicator()));
  }
}

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  static const int _defaultTabIndex = 1;

  final PageController _pageController = PageController(
    initialPage: _defaultTabIndex,
  );
  int _currentPageIndex = _defaultTabIndex;

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  void _onDestinationSelected(int index) {
    setState(() => _currentPageIndex = index);
    _pageController.animateToPage(
      index,
      duration: const Duration(milliseconds: 250),
      curve: Curves.easeInOut,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      drawer: Drawer(
        child: ListView(
          padding: EdgeInsets.zero,
          children: [
            DrawerHeader(
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.primary,
              ),
              child: Text(
                "My Pennies",
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  color: Theme.of(context).colorScheme.onPrimary,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
            ListTile(
              leading: const Icon(Icons.insights_outlined),
              title: const Text("Monthly analytics"),
              onTap: () {
                Navigator.pop(context);
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => TransactionStatsScreen(
                      initialEndDate: DateTime.now(),
                      initialGroupByMonth: true,
                    ),
                  ),
                );
              },
            ),
            ListTile(
              leading: const Icon(Icons.settings_outlined),
              title: const Text("Settings"),
              onTap: () {
                Navigator.pop(context);
                Navigator.pushNamed(context, "/settings");
              },
            ),
          ],
        ),
      ),
      body: PageView(
        controller: _pageController,
        physics: const NeverScrollableScrollPhysics(),
        onPageChanged: (index) => setState(() => _currentPageIndex = index),
        children: const [
          AccountScreen(),
          TransactionScreen(),
          CategoryScreen(),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentPageIndex,
        onDestinationSelected: _onDestinationSelected,
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.account_balance_outlined),
            selectedIcon: Icon(Icons.account_balance),
            label: "Accounts",
          ),
          NavigationDestination(
            icon: Icon(Icons.swap_horiz_outlined),
            selectedIcon: Icon(Icons.swap_horiz),
            label: "Transactions",
          ),
          NavigationDestination(
            icon: Icon(Icons.folder_outlined),
            selectedIcon: Icon(Icons.folder),
            label: "Categories",
          ),
        ],
      ),
    );
  }
}
