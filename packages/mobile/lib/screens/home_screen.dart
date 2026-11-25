import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../state/vault_provider.dart';
import 'vault_screen.dart';
import 'shares_screen.dart';
import 'settings_screen.dart';
import 'status_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int idx = 0;
  @override
  Widget build(BuildContext context) {
    final v = context.watch<VaultProvider>();
    final pages = [
      const VaultScreen(),
      const SharesScreen(),
      const StatusScreen(),
      const SettingsScreen(),
    ];
    return Scaffold(
      appBar: AppBar(
        title: const Text('CryptaVault'),
        actions: [
          if (v.currentWorkspace != null)
            Padding(padding: const EdgeInsets.only(right: 8), child: Center(child: Text(v.currentWorkspace!.name, style: const TextStyle(color: Colors.white70, fontSize: 12)))),
          IconButton(icon: const Icon(Icons.lock_outline), onPressed: v.lock, tooltip: 'Lock'),
        ],
      ),
      body: pages[idx],
      bottomNavigationBar: NavigationBar(
        selectedIndex: idx,
        onDestinationSelected: (i) => setState(() => idx = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.folder_outlined), label: 'Vault'),
          NavigationDestination(icon: Icon(Icons.share_outlined), label: 'Shares'),
          NavigationDestination(icon: Icon(Icons.monitor_heart_outlined), label: 'Status'),
          NavigationDestination(icon: Icon(Icons.settings_outlined), label: 'Settings'),
        ],
      ),
    );
  }
}
