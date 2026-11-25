import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'state/vault_provider.dart';
import 'screens/auth_screen.dart';
import 'screens/home_screen.dart';

class CryptaVaultApp extends StatelessWidget {
  const CryptaVaultApp({super.key});
  @override
  Widget build(BuildContext context) {
    final base = ThemeData.dark(useMaterial3: true);
    return MaterialApp(
      title: 'CryptaVault',
      debugShowCheckedModeBanner: false,
      theme: base.copyWith(
        colorScheme: base.colorScheme.copyWith(
          primary: const Color(0xFF00D4FF),
          secondary: const Color(0xFF7C3AED),
          surface: const Color(0xFF0F1523),
        ),
        scaffoldBackgroundColor: const Color(0xFF080B11),
        cardTheme: const CardThemeData(color: Color(0xFF0F1523), margin: EdgeInsets.zero),
        inputDecorationTheme: InputDecorationTheme(
          filled: true, fillColor: const Color(0xFF121A2B),
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: Color(0x22FFFFFF))),
          enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: Color(0x22FFFFFF))),
          focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: Color(0xFF00D4FF))),
        ),
      ),
      home: Consumer<VaultProvider>(builder: (context, v, _) {
        if (v.status == VaultStatus.loading) {
          return const Scaffold(body: Center(child: CircularProgressIndicator()));
        }
        if (v.status == VaultStatus.unlocked) return const HomeScreen();
        return const AuthScreen();
      }),
    );
  }
}
