import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'services/storage_service.dart';
import 'state/vault_provider.dart';
import 'app.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final storage = StorageService();
  final vault = VaultProvider(storage);
  await vault.init();
  runApp(ChangeNotifierProvider.value(value: vault, child: const CryptaVaultApp()));
}
