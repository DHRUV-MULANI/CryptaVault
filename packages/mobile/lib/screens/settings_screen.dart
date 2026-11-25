import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:provider/provider.dart';

import '../services/api_service.dart';
import '../state/vault_provider.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _apiUrl = TextEditingController();
  final _workspaceName = TextEditingController();
  final _displayName = TextEditingController();
  bool _busy = false;
  String? _error;
  String? _health;
  bool _initialized = false;

  @override
  void dispose() {
    _apiUrl.dispose();
    _workspaceName.dispose();
    _displayName.dispose();
    super.dispose();
  }

  Future<void> _checkHealth(VaultProvider v) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final results = <String>[];
      for (final path in ['/health', '/ready']) {
        final r = await http.get(Uri.parse('${v.api.baseUrl}$path')).timeout(
          const Duration(seconds: 10),
        );
        results.add('$path → ${r.statusCode}');
      }
      if (mounted) setState(() => _health = results.join(' · '));
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _saveUrl(VaultProvider v) async {
    if (_apiUrl.text.trim().isEmpty) return;
    setState(() => _busy = true);
    try {
      await v.setApiUrl(_apiUrl.text.trim());
      await v.refresh();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Server URL updated')),
        );
      }
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _createWorkspace(VaultProvider v) async {
    final name = _workspaceName.text.trim();
    if (name.isEmpty) return;
    setState(() => _busy = true);
    try {
      final ws = await v.api.createWorkspace(name);
      await v.refresh();
      v.selectWorkspace(ws.id);
      _workspaceName.clear();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Created workspace ${ws.name}')),
        );
      }
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _saveProfile(VaultProvider v) async {
    final name = _displayName.text.trim();
    if (name.isEmpty) return;
    setState(() => _busy = true);
    try {
      final r = await http.patch(
        Uri.parse('${v.api.baseUrl}/api/auth/me'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ${await v.api.storage.getToken() ?? ''}',
        },
        body: '{"display_name": ${jsonEncode(name)}}',
      );
      if (r.statusCode >= 400) throw ApiException(r.statusCode, r.body);
      await v.refresh();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Profile updated')),
        );
      }
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final v = context.watch<VaultProvider>();
    if (!_initialized) {
      _apiUrl.text = v.api.baseUrl;
      _displayName.text = v.user?.displayName ?? '';
      _initialized = true;
    }
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Text(_error!, style: const TextStyle(color: Colors.redAccent)),
            ),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text('Account',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  Text(v.user?.email ?? ''),
                  Text(
                    'Role: ${v.user?.role ?? '?'} · Default profile: '
                    '${v.user?.defaultProfile ?? '?'}',
                    style: const TextStyle(fontSize: 12, color: Colors.white60),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _displayName,
                    decoration: const InputDecoration(labelText: 'Display name'),
                  ),
                  const SizedBox(height: 8),
                  FilledButton(
                    onPressed: _busy ? null : () => _saveProfile(v),
                    child: const Text('Save profile'),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text('Workspaces',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  if (v.workspaces.isEmpty)
                    const Text('No workspaces yet.',
                        style: TextStyle(color: Colors.white60)),
                  for (final ws in v.workspaces)
                    ListTile(
                      leading: const Icon(Icons.folder_outlined),
                      title: Text(ws.name),
                      subtitle: Text('${ws.role} · ${ws.defaultProfile}'),
                      selected: v.currentWorkspaceId == ws.id ||
                          (v.currentWorkspaceId == null && v.workspaces.first == ws),
                      onTap: () => v.selectWorkspace(ws.id),
                    ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _workspaceName,
                    decoration: const InputDecoration(
                      labelText: 'New workspace name',
                    ),
                  ),
                  const SizedBox(height: 8),
                  FilledButton(
                    onPressed: _busy ? null : () => _createWorkspace(v),
                    child: const Text('Create workspace'),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text('Connection',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _apiUrl,
                    decoration: const InputDecoration(
                      labelText: 'API / site URL',
                      hintText: 'https://cryptavault.dhruvmulani.com',
                    ),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      FilledButton(
                        onPressed: _busy ? null : () => _saveUrl(v),
                        child: const Text('Save URL'),
                      ),
                      const SizedBox(width: 8),
                      OutlinedButton(
                        onPressed: _busy ? null : () => _checkHealth(v),
                        child: const Text('Check health'),
                      ),
                    ],
                  ),
                  if (_health != null) ...[
                    const SizedBox(height: 8),
                    Text(_health!, style: const TextStyle(color: Colors.greenAccent)),
                  ],
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text('Zero-knowledge boundary',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  const Text(
                    'Your passphrase and master key never leave this device. '
                    'The server only sees ciphertext, wrapped keys, and encrypted '
                    'metadata. Lock the vault to clear the master key from memory.',
                    style: TextStyle(fontSize: 12, color: Colors.white70),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      OutlinedButton.icon(
                        onPressed: v.lock,
                        icon: const Icon(Icons.lock_outline),
                        label: const Text('Lock'),
                      ),
                      const SizedBox(width: 8),
                      FilledButton.icon(
                        onPressed: v.logout,
                        icon: const Icon(Icons.logout),
                        label: const Text('Sign out'),
                        style: FilledButton.styleFrom(
                            backgroundColor: Colors.redAccent),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 80),
        ],
      ),
    );
  }
}
