import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../state/vault_provider.dart';

class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key});
  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  bool register = false;
  bool busy = false;
  String? error;
  final email = TextEditingController();
  final pass = TextEditingController();
  final name = TextEditingController();
  final apiUrl = TextEditingController();

  @override
  void dispose() { email.dispose(); pass.dispose(); name.dispose(); apiUrl.dispose(); super.dispose(); }

  Future<void> _submit(VaultProvider v) async {
    setState(() { busy = true; error = null; });
    try {
      if (apiUrl.text.trim().isNotEmpty) await v.setApiUrl(apiUrl.text.trim());
      if (v.status == VaultStatus.locked) {
        await v.unlock(pass.text);
      } else if (register) {
        await v.register(email.text, pass.text, name.text);
      } else {
        await v.login(email.text, pass.text);
      }
    } catch (e) {
      setState(() { error = e.toString(); });
    } finally {
      if (mounted) setState(() { busy = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    final v = context.watch<VaultProvider>();
    final locked = v.status == VaultStatus.locked;
    return Scaffold(
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 460),
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                  const Icon(Icons.shield_outlined, size: 48, color: Color(0xFF00D4FF)),
                  const SizedBox(height: 12),
                  Text(locked ? 'Unlock Vault' : (register ? 'Create Account' : 'Sign In'), style: Theme.of(context).textTheme.headlineSmall, textAlign: TextAlign.center),
                  const SizedBox(height: 8),
                  Text(locked ? 'Enter your passphrase to decrypt your master key locally.' : 'Zero-knowledge encryption. Your passphrase never leaves this device.',
                    textAlign: TextAlign.center, style: const TextStyle(color: Colors.white70)),
                  const SizedBox(height: 20),
                  if (!locked) ...[
                    TextField(controller: email, decoration: const InputDecoration(labelText: 'Email'), keyboardType: TextInputType.emailAddress),
                    const SizedBox(height: 12),
                    if (register) ...[
                      TextField(controller: name, decoration: const InputDecoration(labelText: 'Display name (optional)')),
                      const SizedBox(height: 12),
                    ],
                  ] else ...[
                    Text('Account: ${v.user?.email ?? ''}', style: const TextStyle(color: Colors.white70)),
                    const SizedBox(height: 12),
                  ],
                  TextField(controller: pass, decoration: const InputDecoration(labelText: 'Passphrase'), obscureText: true),
                  const SizedBox(height: 12),
                  ExpansionTile(title: const Text('Server settings', style: TextStyle(fontSize: 14)), children: [
                    TextField(controller: apiUrl, decoration: InputDecoration(labelText: 'API URL', hintText: v.api.baseUrl)),
                  ]),
                  if (error != null) ...[const SizedBox(height: 8), Text(error!, style: const TextStyle(color: Colors.redAccent))],
                  const SizedBox(height: 16),
                  FilledButton(
                    onPressed: busy ? null : () => _submit(v),
                    child: busy ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2)) : Text(locked ? 'Unlock' : (register ? 'Create account' : 'Sign in')),
                  ),
                  if (!locked) TextButton(
                    onPressed: () => setState(() => register = !register),
                    child: Text(register ? 'Have an account? Sign in' : 'Need an account? Register'),
                  ),
                  if (locked) TextButton(onPressed: busy ? null : v.logout, child: const Text('Use different account')),
                ]),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
