import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:share_plus/share_plus.dart';

import '../models/types.dart';
import '../services/crypto_service.dart';
import '../state/vault_provider.dart';
import 'share_viewer_screen.dart';

class SharesScreen extends StatefulWidget {
  const SharesScreen({super.key});

  @override
  State<SharesScreen> createState() => _SharesScreenState();
}

class _SharesScreenState extends State<SharesScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabs;
  bool _busy = false;
  String? _error;
  List<ApiFile> _files = [];
  List<ApiShare> _mine = [];
  List<ApiShare> _received = [];
  String? _loadedWorkspace;
  ApiShare? _created;
  String? _createdLink;

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

  Future<void> _load(VaultProvider v, {bool force = false}) async {
    final ws = v.currentWorkspace?.id;
    if (ws == null || v.masterKey == null) return;
    if (!force && _loadedWorkspace == ws && _mine.isNotEmpty) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final files = await v.api.listFiles(ws);
      final mine = await v.api.listShares();
      var received = <ApiShare>[];
      try {
        received = await v.api.receivedShares();
      } catch (_) {
        // Recipient inbox is best-effort; older servers may not expose it.
      }
      if (!mounted) return;
      setState(() {
        _files = files;
        _mine = mine;
        _received = received;
        _loadedWorkspace = ws;
      });
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<String> _linkForAsync(VaultProvider v, ApiShare share) async {
    String base = share.shareUrl;
    if (base.isEmpty) {
      base = '${v.api.baseUrl}/#/s/${share.token}';
    }
    final file = _files.where((f) => f.id == share.fileId).firstOrNull;
    if (file == null || v.masterKey == null) return base;
    try {
      final rawKey = await unwrapRawKey(
        v.masterKey!,
        Sealed(ivB64: file.wrappedIv, ctB64: file.wrappedKey),
        'filekey:${file.id}',
      );
      final sep = base.contains('?') ? '&' : '?';
      return '$base${sep}k=${bytesToB64Url(rawKey)}';
    } catch (_) {
      return base;
    }
  }

  Future<void> _copy(VaultProvider v, ApiShare share) async {
    final link = await _linkForAsync(v, share);
    await Clipboard.setData(ClipboardData(text: link));
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Link copied (decryption key included)')),
      );
    }
  }

  Future<void> _showQr(VaultProvider v, ApiShare share) async {
    final link = await _linkForAsync(v, share);
    if (!mounted) return;
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Share QR code'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              QrImageView(data: link, version: QrVersions.auto, size: 240),
              const SizedBox(height: 12),
              SelectableText(link, style: const TextStyle(fontSize: 11)),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Close'),
          ),
          FilledButton(
            onPressed: () => SharePlus.instance.share(ShareParams(text: link)),
            child: const Text('Share'),
          ),
        ],
      ),
    );
  }

  Future<void> _create(VaultProvider v) async {
    if (_files.isEmpty || v.masterKey == null) return;
    ApiFile? selected = _files.first;
    final pinController = TextEditingController();
    final recipientController = TextEditingController();
    final passwordController = TextEditingController();
    final hoursController = TextEditingController(text: '168');
    final usesController = TextEditingController(text: '5');
    String profile = 'BALANCED';

    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialog) => AlertDialog(
          title: const Text('Create secure share'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                DropdownButtonFormField<ApiFile>(
                  initialValue: selected,
                  decoration: const InputDecoration(labelText: 'File'),
                  items: [
                    for (final f in _files)
                      DropdownMenuItem(
                        value: f,
                        child: Text(
                          '${f.id.substring(0, 8)} · ${f.profile} · v${f.currentVersion}',
                        ),
                      ),
                  ],
                  onChanged: (val) {
                    setDialog(() {
                      selected = val;
                      profile = val?.profile ?? profile;
                    });
                  },
                ),
                const SizedBox(height: 10),
                TextField(
                  controller: recipientController,
                  decoration: const InputDecoration(
                    labelText: 'Recipient email (optional)',
                    hintText: 'Logged-in recipient skips the PIN',
                  ),
                ),
                const SizedBox(height: 10),
                TextField(
                  controller: pinController,
                  decoration: const InputDecoration(
                    labelText: '8-digit PIN (optional)',
                    hintText: 'Auto-assigned if blank',
                  ),
                  keyboardType: TextInputType.number,
                  inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                  maxLength: 8,
                ),
                const SizedBox(height: 6),
                TextField(
                  controller: passwordController,
                  decoration: const InputDecoration(
                    labelText: 'Password (optional)',
                  ),
                  obscureText: true,
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: hoursController,
                        decoration: const InputDecoration(labelText: 'Expires in (hours)'),
                        keyboardType: TextInputType.number,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: TextField(
                        controller: usesController,
                        decoration: const InputDecoration(labelText: 'Max downloads'),
                        keyboardType: TextInputType.number,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: const Text('Create'),
            ),
          ],
        ),
      ),
    );
    if (ok != true || selected == null) return;

    final pin = pinController.text.trim();
    if (pin.isNotEmpty && pin.length != 8) {
      if (mounted) setState(() => _error = 'PIN must be exactly 8 digits');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final expires = DateTime.now().toUtc().add(
            Duration(hours: int.tryParse(hoursController.text) ?? 168),
          );
      final payload = <String, dynamic>{
        'file_id': selected!.id,
        'version': selected!.currentVersion,
        'max_uses': int.tryParse(usesController.text) ?? 5,
        'expires_at': expires.toIso8601String(),
        if (pin.isNotEmpty) 'pin': pin,
        if (recipientController.text.trim().isNotEmpty)
          'recipient_email': recipientController.text.trim(),
        if (passwordController.text.isNotEmpty)
          'password': passwordController.text,
      };
      final share = await v.api.createShare(payload);
      final link = await _linkForAsync(v, share);
      await _load(v, force: true);
      if (!mounted) return;
      setState(() {
        _created = share;
        _createdLink = link;
      });
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _changePin(VaultProvider v, ApiShare share) async {
    final controller = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Change PIN'),
        content: TextField(
          controller: controller,
          decoration: const InputDecoration(
            labelText: 'New 8-digit PIN (blank = auto)',
          ),
          keyboardType: TextInputType.number,
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          maxLength: 8,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Save'),
          ),
        ],
      ),
    );
    if (ok != true) return;
    final pin = controller.text.trim();
    if (pin.isNotEmpty && pin.length != 8) {
      if (mounted) setState(() => _error = 'PIN must be exactly 8 digits');
      return;
    }
    setState(() => _busy = true);
    try {
      final updated = await v.api.updateSharePin(share.token, pin: pin.isEmpty ? null : pin);
      await _load(v, force: true);
      if (!mounted) return;
      setState(() {
        _created = updated;
        _createdLink = null;
      });
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _regenerate(VaultProvider v, ApiShare share) async {
    setState(() => _busy = true);
    try {
      final updated = await v.api.regenerateShare(share.token);
      final link = await _linkForAsync(v, updated);
      await _load(v, force: true);
      if (!mounted) return;
      setState(() {
        _created = updated;
        _createdLink = link;
      });
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _revoke(VaultProvider v, ApiShare share) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Revoke share?'),
        content: const Text('The link will stop working immediately.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: FilledButton.styleFrom(backgroundColor: Colors.redAccent),
            child: const Text('Revoke'),
          ),
        ],
      ),
    );
    if (ok != true) return;
    setState(() => _busy = true);
    try {
      await v.api.revokeShare(share.token);
      await _load(v, force: true);
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _openViewer({String? link}) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => ShareViewerScreen(initialLink: link),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final v = context.watch<VaultProvider>();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_busy) _load(v);
    });
    return Column(
      children: [
        if (_error != null)
          Padding(
            padding: const EdgeInsets.all(8),
            child: Text(_error!, style: const TextStyle(color: Colors.redAccent)),
          ),
        if (_created != null && _createdLink != null)
          Card(
            margin: const EdgeInsets.fromLTRB(12, 8, 12, 0),
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text('Share created', style: TextStyle(fontWeight: FontWeight.bold)),
                  const SizedBox(height: 6),
                  SelectableText(
                    _created!.pin != null ? 'PIN: ${_created!.pin}' : 'No PIN',
                    style: const TextStyle(color: Color(0xFF00D4FF)),
                  ),
                  const SizedBox(height: 4),
                  SelectableText(
                    _createdLink!,
                    style: const TextStyle(fontSize: 10, color: Colors.white60),
                    maxLines: 2,
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    children: [
                      FilledButton.icon(
                        onPressed: () => _copy(v, _created!),
                        icon: const Icon(Icons.copy, size: 16),
                        label: const Text('Copy link'),
                      ),
                      OutlinedButton.icon(
                        onPressed: () => _showQr(v, _created!),
                        icon: const Icon(Icons.qr_code, size: 16),
                        label: const Text('QR'),
                      ),
                      OutlinedButton(
                        onPressed: () => _openViewer(link: _createdLink),
                        child: const Text('Open'),
                      ),
                      TextButton(
                        onPressed: () => setState(() {
                          _created = null;
                          _createdLink = null;
                        }),
                        child: const Text('Done'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        TabBar(controller: _tabs, tabs: const [
          Tab(text: 'My shares'),
          Tab(text: 'Shared with me'),
        ]),
        Expanded(
          child: TabBarView(
            controller: _tabs,
            children: [
              _shareList(v, _mine, owned: true),
              _shareList(v, _received, owned: false),
            ],
          ),
        ),
      ],
    );
  }

  Widget _shareList(VaultProvider v, List<ApiShare> shares, {required bool owned}) {
    if (_busy && shares.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }
    if (shares.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(owned ? 'No shares created yet.' : 'Nothing shared with you yet.'),
            const SizedBox(height: 12),
            if (owned)
              FilledButton.icon(
                onPressed: () => _create(v),
                icon: const Icon(Icons.add_link),
                label: const Text('Create share'),
              ),
            OutlinedButton.icon(
              onPressed: () => _openViewer(),
              icon: const Icon(Icons.link),
              label: const Text('Open share link'),
            ),
          ],
        ),
      );
    }
    return Stack(
      children: [
        ListView.separated(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 90),
          itemCount: shares.length,
          separatorBuilder: (_, _) => const SizedBox(height: 8),
          itemBuilder: (ctx, i) {
            final s = shares[i];
            final active = !s.revoked && s.remainingUses > 0;
            return Card(
              child: ListTile(
                leading: Icon(
                  s.pinProtected ? Icons.key : Icons.link,
                  color: active ? const Color(0xFF00D4FF) : Colors.grey,
                ),
                title: Text(
                  '${s.fileId.substring(0, 8)} · ${s.recipientEmail ?? 'anyone'}',
                  style: TextStyle(
                    decoration: active ? null : TextDecoration.lineThrough,
                  ),
                ),
                subtitle: Text(
                  '${s.remainingUses}/${s.maxUses} uses · ${s.expiresAt ?? 'no expiry'}'
                  '${s.passwordProtected ? ' · password' : ''}',
                  style: const TextStyle(fontSize: 11),
                ),
                trailing: owned
                    ? Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          IconButton(
                            icon: const Icon(Icons.copy),
                            tooltip: 'Copy link',
                            onPressed: _busy ? null : () => _copy(v, s),
                          ),
                          IconButton(
                            icon: const Icon(Icons.qr_code),
                            tooltip: 'QR code',
                            onPressed: _busy ? null : () => _showQr(v, s),
                          ),
                          PopupMenuButton<String>(
                            onSelected: (action) {
                              switch (action) {
                                case 'pin':
                                  _changePin(v, s);
                                case 'regen':
                                  _regenerate(v, s);
                                case 'revoke':
                                  _revoke(v, s);
                                case 'open':
                                  _openViewer();
                              }
                            },
                            itemBuilder: (_) => const [
                              PopupMenuItem(value: 'open', child: Text('Open link')),
                              PopupMenuItem(value: 'pin', child: Text('Change PIN')),
                              PopupMenuItem(value: 'regen', child: Text('Regenerate link')),
                              PopupMenuItem(value: 'revoke', child: Text('Revoke')),
                            ],
                          ),
                        ],
                      )
                    : IconButton(
                        icon: const Icon(Icons.open_in_new),
                        tooltip: 'Open share',
                        onPressed: () => _openViewer(),
                      ),
              ),
            );
          },
        ),
        if (owned && !_busy)
          Positioned(
            right: 16,
            bottom: 16,
            child: FloatingActionButton(
              onPressed: () => _create(v),
              child: const Icon(Icons.add_link),
            ),
          ),
      ],
    );
  }
}
