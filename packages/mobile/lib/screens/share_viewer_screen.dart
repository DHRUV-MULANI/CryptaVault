import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:provider/provider.dart';

import '../services/crypto_service.dart' as crypto;
import '../services/share_link.dart';
import '../state/vault_provider.dart';

class ShareViewerScreen extends StatefulWidget {
  final String? initialLink;
  const ShareViewerScreen({super.key, this.initialLink});

  @override
  State<ShareViewerScreen> createState() => _ShareViewerScreenState();
}

class _ShareViewerScreenState extends State<ShareViewerScreen> {
  final _link = TextEditingController();
  final _pin = TextEditingController();
  final _password = TextEditingController();
  bool _busy = false;
  String? _error;
  String? _token;
  String? _keyB64Url;
  String? _fileName;
  String? _fileType;
  String? _fileHash;
  int? _fileSize;
  bool _needsPin = false;
  bool _needsPassword = false;
  Map<String, dynamic>? _info;

  @override
  void initState() {
    super.initState();
    if (widget.initialLink != null) {
      _link.text = widget.initialLink!;
    }
  }

  @override
  void dispose() {
    _link.dispose();
    _pin.dispose();
    _password.dispose();
    super.dispose();
  }

  void _parse() {
    final raw = _link.text.trim();
    if (raw.isEmpty) {
      setState(() {
        _token = null;
        _keyB64Url = null;
        _fileName = null;
        _fileType = null;
        _fileHash = null;
        _fileSize = null;
        _error = 'Paste a share link first.';
      });
      return;
    }
    final parsed = parseServerShareLink(raw);
    setState(() {
      _token = parsed.token;
      _keyB64Url = parsed.keyB64Url;
      _fileName = parsed.name;
      _fileType = parsed.type;
      _fileHash = parsed.hash;
      _fileSize = parsed.size;
      _error = null;
      _info = null;
      _needsPin = false;
      _needsPassword = false;
    });
  }

  Future<void> _loadInfo(VaultProvider v) async {
    if (_token == null) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final info = await v.api.shareInfo(_token!);
      if (!mounted) return;
      setState(() {
        _info = info;
        _needsPin = info['pin_required'] == true;
        _needsPassword = info['password_protected'] == true;
      });
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _download(VaultProvider v) async {
    if (_token == null) return;
    if (_keyB64Url == null || _keyB64Url!.isEmpty) {
      setState(
        () => _error =
            'Missing decryption key. The full link must include #...?k=<key>.',
      );
      return;
    }
    if (_needsPin && _pin.text.trim().length != 8) {
      setState(() => _error = 'Enter the 8-digit PIN.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final rawKey = crypto.b64UrlToBytes(_keyB64Url!);
      final ciphertext = await v.api.downloadShare(
        _token!,
        password: _password.text.isNotEmpty ? _password.text : null,
        pin: _pin.text.isNotEmpty ? _pin.text.trim() : null,
      );
      final container = crypto.Container.fromJson(
        Map<String, dynamic>.from(jsonDecode(utf8.decode(ciphertext)) as Map),
      );
      final bytes = await crypto.decryptContainer(container, rawKey);
      if (_fileHash != null && _fileHash!.isNotEmpty) {
        final actual = await crypto.sha256Hex(bytes);
        if (actual != _fileHash) {
          throw Exception(
            'Integrity check failed: decrypted file hash does not match.',
          );
        }
      }
      if (_fileSize != null && bytes.length != _fileSize) {
        throw Exception(
          'Integrity check failed: decrypted file size does not match.',
        );
      }
      final dir =
          await getDownloadsDirectory() ??
          await getApplicationDocumentsDirectory();
      final tokenPart = _token!.length > 8 ? _token!.substring(0, 8) : _token!;
      final name = safeShareFileName(
        _fileName != null && _fileName!.isNotEmpty
            ? _fileName!
            : 'cryptavault-$tokenPart',
      );
      final out = File('${dir.path}${Platform.pathSeparator}$name');
      await out.writeAsBytes(bytes);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Saved decrypted file to ${out.path}')),
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
    return Scaffold(
      appBar: AppBar(title: const Text('Open share')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              'Paste the full share link. The key and original file name stay in the link fragment and never go to the server.',
              style: TextStyle(color: Colors.white70),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _link,
              decoration: const InputDecoration(
                labelText: 'Share link',
                hintText: 'https://.../#/s/<token>?k=<key>',
              ),
              maxLines: 2,
            ),
            const SizedBox(height: 8),
            OutlinedButton(onPressed: _parse, child: const Text('Parse link')),
            if (_token != null) ...[
              const SizedBox(height: 16),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      if (_fileName != null && _fileName!.isNotEmpty)
                        Text(
                          _fileName!,
                          style: const TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      if (_fileType != null && _fileType!.isNotEmpty)
                        Text(
                          '${_fileType!} · ${_fileSize ?? '?'} bytes',
                          style: const TextStyle(
                            fontSize: 11,
                            color: Colors.white60,
                          ),
                        ),
                      SelectableText(
                        'Token: $_token',
                        style: const TextStyle(fontSize: 12),
                      ),
                      Text(
                        'Key fragment: ${_keyB64Url != null ? 'present' : 'MISSING'}',
                        style: TextStyle(
                          color: _keyB64Url != null
                              ? Colors.greenAccent
                              : Colors.redAccent,
                          fontSize: 12,
                        ),
                      ),
                      if (_info != null)
                        Text(
                          'Expires: ${_info!['expires_at'] ?? 'never'} · '
                          'Uses left: ${_info!['remaining_uses'] ?? '?'}',
                          style: const TextStyle(
                            fontSize: 11,
                            color: Colors.white60,
                          ),
                        ),
                      const SizedBox(height: 8),
                      FilledButton(
                        onPressed: _busy ? null : () => _loadInfo(v),
                        child: const Text('Check link requirements'),
                      ),
                      if (_needsPin) ...[
                        const SizedBox(height: 12),
                        TextField(
                          controller: _pin,
                          decoration: const InputDecoration(
                            labelText: '8-digit PIN',
                          ),
                          keyboardType: TextInputType.number,
                          maxLength: 8,
                        ),
                      ],
                      if (_needsPassword) ...[
                        const SizedBox(height: 8),
                        TextField(
                          controller: _password,
                          decoration: const InputDecoration(
                            labelText: 'Password',
                          ),
                          obscureText: true,
                        ),
                      ],
                      const SizedBox(height: 12),
                      FilledButton.icon(
                        onPressed: _busy ? null : () => _download(v),
                        icon: const Icon(Icons.download),
                        label: const Text('Download & decrypt'),
                      ),
                    ],
                  ),
                ),
              ),
            ],
            if (_error != null) ...[
              const SizedBox(height: 12),
              Text(_error!, style: const TextStyle(color: Colors.redAccent)),
            ],
            if (_busy) ...[
              const SizedBox(height: 16),
              const Center(child: CircularProgressIndicator()),
            ],
          ],
        ),
      ),
    );
  }
}
