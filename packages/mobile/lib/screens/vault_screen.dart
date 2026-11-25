import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:provider/provider.dart';

import '../models/types.dart';
import '../services/api_service.dart';
import '../services/crypto_service.dart' as crypto;
import '../state/vault_provider.dart';

class VaultScreen extends StatefulWidget {
  const VaultScreen({super.key});

  @override
  State<VaultScreen> createState() => _VaultScreenState();
}

class _VaultScreenState extends State<VaultScreen> {
  final _search = TextEditingController();
  bool _busy = false;
  String? _error;
  String? _folderFilter;
  List<ApiFile> _files = [];
  String? _loadedWorkspace;

  static const _profiles = [
    'PERFORMANCE',
    'STANDARD',
    'BALANCED',
    'STRONG',
    'PQ_STRONG',
    'MAXIMUM',
  ];

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  Future<void> _load(VaultProvider v, {bool force = false}) async {
    final ws = v.currentWorkspace?.id;
    if (ws == null || v.masterKey == null) return;
    if (!force && _loadedWorkspace == ws) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final files = await v.api.listFiles(ws);
      if (!mounted) return;
      setState(() {
        _files = files;
        _loadedWorkspace = ws;
        _folderFilter = null;
      });
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<FileMeta?> _decryptMeta(VaultProvider v, ApiFile file) async {
    try {
      final json = await crypto.openJson(
        v.masterKey!,
        Sealed(ivB64: file.metaIv, ctB64: file.encryptedMeta),
        aad: 'filemeta:${file.id}',
      );
      return FileMeta.fromJson(json);
    } catch (_) {
      return null;
    }
  }

  Future<void> _upload(VaultProvider v) async {
    final ws = v.currentWorkspace?.id;
    if (ws == null || v.masterKey == null) return;
    final pickedFiles = await FilePicker.pickFiles();
    if (pickedFiles.isEmpty) return;
    final picked = pickedFiles.first;
    final bytes = await picked.readAsBytes();
    if (!mounted) return;
    String profile = v.currentWorkspace!.defaultProfile;
    if (!_profiles.contains(profile)) profile = 'BALANCED';
    final folderController = TextEditingController();
    final result = await showDialog<_UploadOptions>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Encrypt & upload'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(picked.name, style: const TextStyle(color: Colors.white70)),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              initialValue: profile,
              decoration: const InputDecoration(labelText: 'Encryption profile'),
              items: [
                for (final p in _profiles)
                  DropdownMenuItem(value: p, child: Text(p)),
              ],
              onChanged: (val) => profile = val ?? profile,
            ),
            const SizedBox(height: 12),
            TextField(
              controller: folderController,
              decoration: const InputDecoration(
                labelText: 'Folder (optional)',
                hintText: 'e.g. Documents',
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(
              ctx,
              _UploadOptions(profile, folderController.text.trim()),
            ),
            child: const Text('Upload'),
          ),
        ],
      ),
    );
    if (result == null) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final enc = await crypto.encryptFile(
        name: picked.name,
        mime: picked.extension != null
            ? _guessMime(picked.extension!)
            : 'application/octet-stream',
        bytes: Uint8List.fromList(bytes),
        profile: result.profile,
        chunkSize: 1024 * 1024,
        folder: result.folder.isEmpty ? null : result.folder,
        onProgress: (fraction) {
          // Progress is intentionally not rebuilt for each chunk.
        },
      );
      final meta = await crypto.sealJson(
        v.masterKey!,
        enc.meta.toJson(),
        aad: 'filemeta:${enc.container.fileId}',
      );
      final wrapped = await crypto.wrapRawKey(
        v.masterKey!,
        enc.rawKey,
        'filekey:${enc.container.fileId}',
      );
      final containerBytes = Uint8List.fromList(
        utf8.encode(jsonEncode(enc.container.toJson())),
      );
      await v.api.uploadFile(
        workspaceId: ws,
        fileId: enc.container.fileId,
        encryptedMeta: meta.ctB64,
        metaIv: meta.ivB64,
        wrappedKey: wrapped.ctB64,
        wrappedIv: wrapped.ivB64,
        contentTag: '',
        profile: result.profile,
        ciphertext: containerBytes,
      );
      await _load(v, force: true);
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _download(VaultProvider v, ApiFile file) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final meta = await _decryptMeta(v, file) ??
          FileMeta(
            name: file.id,
            type: 'application/octet-stream',
            size: 0,
            hash: '',
            chunkCount: 0,
            compression: 'none',
            profile: file.profile,
            createdAt: '',
          );
      final containerBytes = await v.api.downloadFile(file.id);
      final container = crypto.Container.fromJson(
        Map<String, dynamic>.from(jsonDecode(utf8.decode(containerBytes)) as Map),
      );
      final rawKey = await crypto.unwrapRawKey(
        v.masterKey!,
        Sealed(ivB64: file.wrappedIv, ctB64: file.wrappedKey),
        'filekey:${file.id}',
      );
      final plain = await crypto.decryptContainer(container, rawKey);
      final digest = await crypto.sha256Hex(plain);
      if (meta.hash.isNotEmpty && digest != meta.hash) {
        throw ApiException(0, 'Integrity check failed: hash mismatch');
      }
      final dir = await getDownloadsDirectory() ?? await getApplicationDocumentsDirectory();
      var name = meta.name.replaceAll(RegExp(r'[/\\]'), '_');
      var out = File('${dir.path}${Platform.pathSeparator}$name');
      var counter = 1;
      while (out.existsSync()) {
        final dot = name.lastIndexOf('.');
        final base = dot > 0 ? name.substring(0, dot) : name;
        final ext = dot > 0 ? name.substring(dot) : '';
        out = File(
          '${dir.path}${Platform.pathSeparator}$base ($counter)$ext',
        );
        counter++;
      }
      await out.writeAsBytes(plain);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Saved to ${out.path}')),
        );
      }
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _trash(VaultProvider v, ApiFile file) async {
    setState(() => _busy = true);
    try {
      await v.api.trashFile(file.id);
      await _load(v, force: true);
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _restore(VaultProvider v, ApiFile file) async {
    setState(() => _busy = true);
    try {
      await v.api.untrashFile(file.id);
      await _load(v, force: true);
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _delete(VaultProvider v, ApiFile file) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete permanently?'),
        content: const Text(
          'This removes the ciphertext and all versions. It cannot be undone.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: FilledButton.styleFrom(backgroundColor: Colors.redAccent),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    setState(() => _busy = true);
    try {
      await v.api.deleteFilePermanent(file.id);
      await _load(v, force: true);
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  String _guessMime(String ext) {
    switch (ext.toLowerCase()) {
      case 'txt':
      case 'md':
        return 'text/plain';
      case 'json':
        return 'application/json';
      case 'pdf':
        return 'application/pdf';
      case 'png':
        return 'image/png';
      case 'jpg':
      case 'jpeg':
        return 'image/jpeg';
      default:
        return 'application/octet-stream';
    }
  }

  @override
  Widget build(BuildContext context) {
    final v = context.watch<VaultProvider>();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_busy) _load(v);
    });
    final query = _search.text.trim().toLowerCase();
    final visible = _files.where((f) {
      if (_folderFilter != null) return true;
      return true;
    }).toList();

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
          child: TextField(
            controller: _search,
            decoration: const InputDecoration(
              hintText: 'Search files (name decrypted on display)',
              prefixIcon: Icon(Icons.search),
            ),
            onChanged: (_) => setState(() {}),
          ),
        ),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Text(_error!, style: const TextStyle(color: Colors.redAccent)),
          ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Row(
            children: [
              Text(
                '${visible.length} file(s)',
                style: const TextStyle(color: Colors.white60, fontSize: 12),
              ),
              const Spacer(),
              if (_folderFilter != null)
                TextButton.icon(
                  onPressed: () => setState(() => _folderFilter = null),
                  icon: const Icon(Icons.clear, size: 14),
                  label: Text('Folder: $_folderFilter'),
                ),
              FilledButton.icon(
                onPressed: _busy ? null : () => _upload(v),
                icon: const Icon(Icons.upload),
                label: const Text('Encrypt & upload'),
              ),
            ],
          ),
        ),
        const SizedBox(height: 8),
        Expanded(
          child: _busy && _files.isEmpty
              ? const Center(child: CircularProgressIndicator())
              : visible.isEmpty
                  ? const Center(
                      child: Text(
                        'No files yet. Upload one to start your encrypted vault.',
                        textAlign: TextAlign.center,
                        style: TextStyle(color: Colors.white60),
                      ),
                    )
                  : ListView.separated(
                      padding: const EdgeInsets.fromLTRB(16, 4, 16, 90),
                      itemCount: visible.length,
                      separatorBuilder: (_, _) => const SizedBox(height: 8),
                      itemBuilder: (ctx, i) {
                        final file = visible[i];
                        return FutureBuilder<FileMeta?>(
                          future: _decryptMeta(v, file),
                          builder: (context, snap) {
                            final meta = snap.data;
                            final name = meta?.name ?? file.id.substring(0, 8);
                            if (query.isNotEmpty &&
                                !name.toLowerCase().contains(query)) {
                              return const SizedBox.shrink();
                            }
                            final trashed = file.deletedAt != null;
                            return Card(
                              child: ListTile(
                                leading: Icon(
                                  trashed ? Icons.delete_outline : Icons.lock_outline,
                                  color: trashed ? Colors.redAccent : const Color(0xFF00D4FF),
                                ),
                                title: Text(name,
                                    style: TextStyle(
                                        decoration:
                                            trashed ? TextDecoration.lineThrough : null)),
                                subtitle: Text(
                                  '${file.profile} · v${file.currentVersion} · '
                                  '${(file.ciphertextSize / 1024).toStringAsFixed(1)} KB'
                                  '${meta?.folder != null ? ' · ${meta!.folder}' : ''}',
                                  style: const TextStyle(fontSize: 11),
                                ),
                                trailing: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    if (!trashed)
                                      IconButton(
                                        icon: const Icon(Icons.download_outlined),
                                        tooltip: 'Download & decrypt',
                                        onPressed: _busy ? null : () => _download(v, file),
                                      ),
                                    if (!trashed)
                                      IconButton(
                                        icon: const Icon(Icons.delete_outline),
                                        tooltip: 'Trash',
                                        onPressed: _busy ? null : () => _trash(v, file),
                                      ),
                                    if (trashed) ...[
                                      IconButton(
                                        icon: const Icon(Icons.restore),
                                        tooltip: 'Restore',
                                        onPressed: _busy ? null : () => _restore(v, file),
                                      ),
                                      IconButton(
                                        icon: const Icon(Icons.delete_forever),
                                        tooltip: 'Delete permanently',
                                        onPressed: _busy ? null : () => _delete(v, file),
                                      ),
                                    ],
                                  ],
                                ),
                              ),
                            );
                          },
                        );
                      },
                    ),
        ),
      ],
    );
  }
}

class _UploadOptions {
  final String profile;
  final String folder;
  const _UploadOptions(this.profile, this.folder);
}
