import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/types.dart';
import '../state/vault_provider.dart';

class StatusScreen extends StatefulWidget {
  const StatusScreen({super.key});

  @override
  State<StatusScreen> createState() => _StatusScreenState();
}

class _StatusScreenState extends State<StatusScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabs;
  bool _busy = false;
  String? _error;
  Map<String, dynamic>? _dashboard;
  Map<String, dynamic>? _adminDashboard;
  Map<String, dynamic>? _health;
  List<ApiUser> _users = [];
  Map<String, bool> _flags = {};

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  Future<void> _load(VaultProvider v) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final dashboard = await v.api.dashboard();
      Map<String, dynamic>? adminDashboard;
      Map<String, dynamic>? health;
      List<ApiUser> users = [];
      Map<String, bool> flags = {};
      if (v.user?.role == 'admin') {
        try {
          adminDashboard = await v.api.adminDashboard();
          health = await v.api.adminHealth();
          users = await v.api.adminUsers();
          flags = await v.api.adminFlags();
        } catch (e) {
          adminDashboard = {'error': e.toString()};
        }
      }
      if (!mounted) return;
      setState(() {
        _dashboard = dashboard;
        _adminDashboard = adminDashboard;
        _health = health;
        _users = users;
        _flags = flags;
      });
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _toggleFlag(VaultProvider v, String name, bool value) async {
    setState(() => _busy = true);
    try {
      await v.api.adminSetFlag(name, !value);
      await _load(v);
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _updateUser(
    VaultProvider v,
    ApiUser user, {
    bool? suspended,
    String? role,
  }) async {
    final payload = <String, dynamic>{
      'suspended': ?suspended,
      'role': ?role,
    };
    setState(() => _busy = true);
    try {
      await v.api.adminUpdateUser(user.id, payload);
      await _load(v);
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  String _bytes(int value) {
    if (value < 1024) return '$value B';
    if (value < 1024 * 1024) return '${(value / 1024).toStringAsFixed(1)} KB';
    if (value < 1024 * 1024 * 1024) {
      return '${(value / (1024 * 1024)).toStringAsFixed(1)} MB';
    }
    return '${(value / (1024 * 1024 * 1024)).toStringAsFixed(2)} GB';
  }

  @override
  Widget build(BuildContext context) {
    final v = context.watch<VaultProvider>();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_busy && _dashboard == null) _load(v);
    });
    return Column(
      children: [
        if (_error != null)
          Padding(
            padding: const EdgeInsets.all(8),
            child: Text(_error!, style: const TextStyle(color: Colors.redAccent)),
          ),
        TabBar(
          controller: _tabs,
          tabs: [
            const Tab(text: 'Status'),
            Tab(text: v.user?.role == 'admin' ? 'Admin' : 'Admin (role required)'),
          ],
        ),
        Expanded(
          child: TabBarView(
            controller: _tabs,
            children: [
              _statusView(v),
              _adminView(v),
            ],
          ),
        ),
      ],
    );
  }

  Widget _statusView(VaultProvider v) {
    if (_busy && _dashboard == null) {
      return const Center(child: CircularProgressIndicator());
    }
    final d = _dashboard ?? {};
    return RefreshIndicator(
      onRefresh: () => _load(v),
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              _stat('Workspaces', '${d['workspaces'] ?? 0}'),
              _stat('Files', '${d['files'] ?? 0}'),
              _stat('Trash', '${d['trash'] ?? 0}'),
              _stat('Active shares', '${d['active_shares'] ?? 0}'),
              _stat('Ciphertext', _bytes((d['bytes'] ?? 0) as int)),
              _stat('Used / quota',
                  '${_bytes((d['used_bytes'] ?? 0) as int)} / ${_bytes((d['quota_bytes'] ?? 0) as int)}'),
            ],
          ),
          const SizedBox(height: 16),
          Text('Storage mix',
              style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          for (final row in (d['storage'] as List? ?? []))
            ListTile(
              dense: true,
              leading: const Icon(Icons.storage_outlined),
              title: Text('${row['target']}'),
              subtitle: Text('${row['files']} files · ${_bytes((row['bytes'] ?? 0) as int)}'),
            ),
        ],
      ),
    );
  }

  Widget _stat(String label, String value) => SizedBox(
        width: 150,
        child: Card(
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label,
                    style: const TextStyle(fontSize: 11, color: Colors.white60)),
                const SizedBox(height: 4),
                Text(value, style: const TextStyle(fontSize: 16)),
              ],
            ),
          ),
        ),
      );

  Widget _adminView(VaultProvider v) {
    if (v.user?.role != 'admin') {
      return const Center(
        child: Text('Admin access requires the admin role.'),
      );
    }
    if (_busy && _adminDashboard == null) {
      return const Center(child: CircularProgressIndicator());
    }
    final h = _health ?? {};
    final a = _adminDashboard ?? {};
    return RefreshIndicator(
      onRefresh: () => _load(v),
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text('System health',
                      style: TextStyle(fontWeight: FontWeight.bold)),
                  const SizedBox(height: 6),
                  Text('Status: ${h['status'] ?? '?'} · Database: ${h['database'] ?? '?'}'),
                  Text('Users: ${h['users'] ?? a['users_total'] ?? '?'} · '
                      'Workspaces: ${h['workspaces'] ?? a['workspaces_total'] ?? '?'}'),
                  Text('Files: ${h['files'] ?? a['files_total'] ?? '?'} · '
                      'Shares: ${h['shares'] ?? a['shares_total'] ?? '?'}'),
                  for (final t in (h['storage_targets'] as List? ?? []))
                    Text('Storage ${t['name']}: ${t['status'] ?? t['healthy'] ?? '?'}',
                        style: const TextStyle(fontSize: 11, color: Colors.white60)),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          const Text('Feature flags', style: TextStyle(fontWeight: FontWeight.bold)),
          for (final entry in _flags.entries)
            SwitchListTile(
              dense: true,
              title: Text(entry.key),
              value: entry.value,
              onChanged: _busy ? null : (val) => _toggleFlag(v, entry.key, entry.value),
            ),
          const SizedBox(height: 12),
          const Text('Users', style: TextStyle(fontWeight: FontWeight.bold)),
          for (final user in _users)
            Card(
              child: ListTile(
                dense: true,
                leading: CircleAvatar(
                    child: Text(user.displayName.isEmpty
                        ? '?'
                        : user.displayName[0].toUpperCase())),
                title: Text(user.email),
                subtitle: Text(
                    '${user.role} · ${user.suspended ? 'suspended' : 'active'} · '
                    '${_bytes(user.usedBytes)} / ${_bytes(user.quotaBytes)}'),
                trailing: PopupMenuButton<String>(
                  onSelected: (action) {
                    if (action == 'suspend') {
                      _updateUser(v, user, suspended: !user.suspended);
                    } else if (action == 'role') {
                      _updateUser(v, user,
                          role: user.role == 'admin' ? 'user' : 'admin');
                    }
                  },
                  itemBuilder: (_) => [
                    PopupMenuItem(
                      value: 'suspend',
                      child: Text(user.suspended ? 'Unsuspend' : 'Suspend'),
                    ),
                    PopupMenuItem(
                      value: 'role',
                      child: Text(user.role == 'admin' ? 'Make user' : 'Make admin'),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}
