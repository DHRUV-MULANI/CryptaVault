import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:share_plus/share_plus.dart';

import '../models/types.dart';
import '../services/crypto_service.dart';
import '../services/share_link.dart';
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
  final Map<String, FileMeta> _metas = {};
  List<ApiShare> _mine = [];
  List<ApiShare> _received = [];
  String? _loadedWorkspace;
  bool _loaded = false;
  final Map<String, Map<String, dynamic>> _shareInfo = {};
  ApiShare? _created;
  String? _createdLink;
  bool _batchCreated = false;

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
    if (!force && _loaded && _loadedWorkspace == ws) return;
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
      final metas = <String, FileMeta>{};
      for (final file in files) {
        if (file.deletedAt != null) continue;
        try {
          final meta = await openJson(
            v.masterKey!,
            Sealed(ivB64: file.metaIv, ctB64: file.encryptedMeta),
            aad: 'filemeta:${file.id}',
          );
          metas[file.id] = FileMeta.fromJson(meta);
        } catch (_) {
          // Keep the file selectable even if its metadata cannot be opened.
        }
      }
      final infos = <String, Map<String, dynamic>>{};
      for (final share in [...mine, ...received]) {
        try {
          infos[share.token] = await v.api.shareInfo(share.token);
        } catch (_) {
          // Revoked/expired shares cannot return policy info; show list fields instead.
        }
      }
      if (!mounted) return;
      setState(() {
        _files = files;
        _metas
          ..clear()
          ..addAll(metas);
        _shareInfo
          ..clear()
          ..addAll(infos);
        _mine = mine;
        _received = received;
        _loadedWorkspace = ws;
      });
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
      _loaded = true;
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
      final meta = _metas[share.fileId];
      if (meta != null) {
        return buildServerShareLink(base, bytesToB64Url(rawKey), meta);
      }
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
                          '${_metas[f.id]?.name ?? f.id.substring(0, 8)} · v${f.currentVersion}',
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
                        decoration: const InputDecoration(
                          labelText: 'Expires in (hours)',
                        ),
                        keyboardType: TextInputType.number,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: TextField(
                        controller: usesController,
                        decoration: const InputDecoration(
                          labelText: 'Max downloads',
                        ),
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
        _batchCreated = false;
      });
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _shareAll(VaultProvider v) async {
    final targets = _files.where((f) => f.deletedAt == null).toList();
    if (targets.isEmpty || v.masterKey == null) return;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Share all files?'),
        content: Text(
          'Create a separate server-enforced share for ${targets.length} file(s) '
          'in this workspace.',
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
    );
    if (ok != true) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final expires = DateTime.now().toUtc().add(const Duration(hours: 168));
      final blocks = <String>[];
      for (final f in targets) {
        final share = await v.api.createShare({
          'file_id': f.id,
          'version': f.currentVersion,
          'max_uses': 5,
          'expires_at': expires.toIso8601String(),
        });
        final rawKey = await unwrapRawKey(
          v.masterKey!,
          Sealed(ivB64: f.wrappedIv, ctB64: f.wrappedKey),
          'filekey:${f.id}',
        );
        final meta = _metas[f.id];
        final link = meta != null
            ? buildServerShareLink(share.shareUrl, bytesToB64Url(rawKey), meta)
            : '${share.shareUrl}?k=${bytesToB64Url(rawKey)}';
        blocks.add(
          '${meta?.name ?? f.id}\n$link\nPIN: ${share.pin ?? '(none)'}',
        );
      }
      await _load(v, force: true);
      if (!mounted) return;
      setState(() {
        _created = null;
        _createdLink = blocks.join('\n\n');
        _batchCreated = true;
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
      final updated = await v.api.updateSharePin(
        share.token,
        pin: pin.isEmpty ? null : pin,
      );
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
      MaterialPageRoute(builder: (_) => ShareViewerScreen(initialLink: link)),
    );
  }

  Future<void> _openShare(VaultProvider v, ApiShare share) async {
    final link = await _linkForAsync(v, share);
    if (!mounted) return;
    _openViewer(link: link);
  }

  int _asInt(dynamic value, [int fallback = 0]) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse(value?.toString() ?? '') ?? fallback;
  }

  String? _text(dynamic value) {
    if (value == null) return null;
    final text = value.toString();
    return text.isEmpty ? null : text;
  }

  int _remaining(ApiShare s) {
    final info = _shareInfo[s.token];
    return _asInt(info?['remaining_uses'], s.remainingUses);
  }

  String _status(ApiShare s) {
    if (s.revoked) return 'Revoked';
    if (_remaining(s) <= 0) return 'Exhausted';
    final info = _shareInfo[s.token];
    final raw = _text(info?['expires_at']) ?? s.expiresAt;
    final expiry = raw == null ? null : DateTime.tryParse(raw);
    if (expiry != null && expiry.toLocal().isBefore(DateTime.now())) {
      return 'Expired';
    }
    return 'Active';
  }

  String _formatBytes(int bytes) {
    if (bytes <= 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    final exponent = (bytes < 1 ? 0 : (bytes.bitLength - 1) ~/ 10).clamp(0, 4);
    final value = bytes / (1 << (10 * exponent));
    return '${value >= 10 ? value.toStringAsFixed(0) : value.toStringAsFixed(1)} ${units[exponent]}';
  }

  Widget _summaryCard(String label, String value) {
    return Expanded(
      child: Card(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 8),
          child: Column(
            children: [
              Text(
                value,
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF00D4FF),
                ),
              ),
              const SizedBox(height: 2),
              Text(
                label,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 10, color: Colors.white60),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final v = context.watch<VaultProvider>();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_busy) _load(v);
    });
    final activeCount = _mine.where((s) => _status(s) == 'Active').length;
    final pinCount = _mine.where((s) => s.pinProtected).length;
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
          child: Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _busy ? null : () => _load(v, force: true),
                  icon: const Icon(Icons.refresh, size: 16),
                  label: const Text('Refresh'),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _busy || _files.isEmpty
                      ? null
                      : () => _shareAll(v),
                  icon: const Icon(Icons.share, size: 16),
                  label: const Text('Share all'),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: FilledButton.icon(
                  onPressed: _busy || _files.isEmpty ? null : () => _create(v),
                  icon: const Icon(Icons.add_link, size: 16),
                  label: const Text('Create'),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 8),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12),
          child: Row(
            children: [
              _summaryCard('Active', '$activeCount'),
              const SizedBox(width: 8),
              _summaryCard('My shares', '${_mine.length}'),
              const SizedBox(width: 8),
              _summaryCard('Received', '${_received.length}'),
              const SizedBox(width: 8),
              _summaryCard('PIN', '$pinCount'),
            ],
          ),
        ),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.all(8),
            child: Text(
              _error!,
              style: const TextStyle(color: Colors.redAccent),
            ),
          ),
        if (_createdLink != null && (_created != null || _batchCreated))
          Card(
            margin: const EdgeInsets.fromLTRB(12, 8, 12, 0),
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    _batchCreated ? 'Shares created' : 'Share created',
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                  if (_created != null)
                    Text(
                      _metas[_created!.fileId]?.name ??
                          _created!.fileId.substring(0, 8),
                      style: const TextStyle(
                        color: Colors.white70,
                        fontSize: 12,
                      ),
                    ),
                  if (_created != null) ...[
                    const SizedBox(height: 6),
                    SelectableText(
                      _created!.pin != null
                          ? 'PIN: ${_created!.pin}'
                          : 'No PIN',
                      style: const TextStyle(color: Color(0xFF00D4FF)),
                    ),
                  ],
                  const SizedBox(height: 4),
                  SelectableText(
                    _createdLink!,
                    style: const TextStyle(fontSize: 10, color: Colors.white60),
                    maxLines: _batchCreated ? 8 : 2,
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    children: [
                      FilledButton.icon(
                        onPressed: () async {
                          final messenger = ScaffoldMessenger.of(context);
                          await Clipboard.setData(
                            ClipboardData(text: _createdLink!),
                          );
                          if (mounted) {
                            messenger.showSnackBar(
                              const SnackBar(content: Text('Links copied')),
                            );
                          }
                        },
                        icon: const Icon(Icons.copy, size: 16),
                        label: Text(_batchCreated ? 'Copy all' : 'Copy link'),
                      ),
                      OutlinedButton.icon(
                        onPressed: () => SharePlus.instance.share(
                          ShareParams(text: _createdLink!),
                        ),
                        icon: const Icon(Icons.share, size: 16),
                        label: const Text('Share'),
                      ),
                      if (_created != null)
                        OutlinedButton.icon(
                          onPressed: () => _showQr(v, _created!),
                          icon: const Icon(Icons.qr_code, size: 16),
                          label: const Text('QR'),
                        ),
                      if (_created != null)
                        OutlinedButton(
                          onPressed: () => _openViewer(link: _createdLink),
                          child: const Text('Open'),
                        ),
                      TextButton(
                        onPressed: () => setState(() {
                          _created = null;
                          _createdLink = null;
                          _batchCreated = false;
                        }),
                        child: const Text('Done'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        TabBar(
          controller: _tabs,
          tabs: const [
            Tab(text: 'My shares'),
            Tab(text: 'Shared with me'),
          ],
        ),
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

  Widget _shareList(
    VaultProvider v,
    List<ApiShare> shares, {
    required bool owned,
  }) {
    if (_busy && shares.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }
    if (shares.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              owned ? 'No shares created yet.' : 'Nothing shared with you yet.',
            ),
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
            final info = _shareInfo[s.token];
            final status = _status(s);
            final active = status == 'Active';
            final version = _asInt(info?['version'], s.version);
            final remaining = _remaining(s);
            final expiry = _text(info?['expires_at']) ?? s.expiresAt;
            final recipient =
                _text(info?['recipient_email']) ?? s.recipientEmail;
            final ciphertext = _asInt(info?['ciphertext_size']);
            final profile = _text(info?['profile']);
            final meta = _metas[s.fileId];
            return Card(
              child: ListTile(
                isThreeLine: true,
                leading: Icon(
                  s.pinProtected ? Icons.key : Icons.link,
                  color: active ? const Color(0xFF00D4FF) : Colors.grey,
                ),
                title: Text(
                  meta?.name ?? s.fileId.substring(0, 8),
                  style: TextStyle(
                    decoration: active ? null : TextDecoration.lineThrough,
                  ),
                ),
                subtitle: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SizedBox(height: 2),
                    Text(
                      'Token: ${s.token.substring(0, s.token.length > 12 ? 12 : s.token.length)}… · v$version · $status',
                      style: const TextStyle(fontSize: 11),
                    ),
                    Text(
                      '${recipient ?? 'Anyone with link'} · $remaining/${s.maxUses} uses',
                      style: const TextStyle(fontSize: 11),
                    ),
                    Text(
                      'Expires: ${expiry ?? 'never'}'
                      '${s.passwordProtected ? ' · password' : ''}'
                      '${s.pinProtected ? ' · PIN' : ''}',
                      style: const TextStyle(fontSize: 11),
                    ),
                    if (ciphertext > 0 || profile != null)
                      Text(
                        '${ciphertext > 0 ? 'Ciphertext: ${_formatBytes(ciphertext)}' : ''}'
                        '${profile != null ? ' · $profile' : ''}',
                        style: const TextStyle(
                          fontSize: 10,
                          color: Colors.white60,
                        ),
                      ),
                  ],
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
                                  _openShare(v, s);
                              }
                            },
                            itemBuilder: (_) => const [
                              PopupMenuItem(
                                value: 'open',
                                child: Text('Open link'),
                              ),
                              PopupMenuItem(
                                value: 'pin',
                                child: Text('Change PIN'),
                              ),
                              PopupMenuItem(
                                value: 'regen',
                                child: Text('Regenerate link'),
                              ),
                              PopupMenuItem(
                                value: 'revoke',
                                child: Text('Revoke'),
                              ),
                            ],
                          ),
                        ],
                      )
                    : IconButton(
                        icon: const Icon(Icons.open_in_new),
                        tooltip: 'Open share',
                        onPressed: () => _openViewer(link: s.shareUrl),
                      ),
              ),
            );
          },
        ),
        if (owned)
          Positioned(
            right: 16,
            bottom: 16,
            child: FloatingActionButton(
              onPressed: _busy || _files.isEmpty ? null : () => _create(v),
              tooltip: 'Create share',
              child: const Icon(Icons.add_link),
            ),
          ),
      ],
    );
  }
}
