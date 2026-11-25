import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import 'package:cryptavault_mobile/models/types.dart';
import 'package:cryptavault_mobile/services/api_service.dart';
import 'package:cryptavault_mobile/services/crypto_service.dart';
import 'package:cryptavault_mobile/services/storage_service.dart';
import 'package:cryptavault_mobile/state/vault_provider.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  final stamp = DateTime.now().microsecondsSinceEpoch;
  final ownerEmail = 'flutter-owner-$stamp@example.com';
  final recipientEmail = 'flutter-recipient-$stamp@example.com';
  const passphrase = 'TestPassphrase!123';

  group('live API interoperability', () {
    late VaultProvider owner;
    late VaultProvider recipient;
    var apiAvailable = false;

    setUpAll(() async {
      try {
        final health = await http
            .get(Uri.parse('http://127.0.0.1:8000/health'))
            .timeout(const Duration(seconds: 3));
        apiAvailable = health.statusCode == 200;
      } catch (_) {
        apiAvailable = false;
      }
      if (!apiAvailable) {
        // Integration test: skip silently when the local API is not running.
        return;
      }
      owner = VaultProvider(MemoryCredentialStore(), baseUrl: 'http://127.0.0.1:8000');
      recipient = VaultProvider(MemoryCredentialStore(), baseUrl: 'http://127.0.0.1:8000');
      await owner.register(ownerEmail, passphrase, 'Flutter Owner');
      await recipient.register(recipientEmail, passphrase, 'Flutter Recipient');
    });

    test('register derives verifier and unlocks vault check', () async {
      expect(owner.status, VaultStatus.unlocked);
      expect(owner.user!.email, ownerEmail);
      expect(owner.workspaces.isNotEmpty, isTrue);
      expect(owner.vault!.kdfIterations, 210000);
    });

    test('login from a fresh session unlocks with the same passphrase', () async {
      final fresh = VaultProvider(MemoryCredentialStore(), baseUrl: 'http://127.0.0.1:8000');
      await fresh.login(ownerEmail, passphrase);
      expect(fresh.status, VaultStatus.unlocked);
      expect(fresh.masterKey, isNotNull);
      fresh.lock();
      expect(fresh.masterKey, isNull);
      await fresh.unlock(passphrase);
      expect(utf8.decode(await open(
        fresh.masterKey!,
        fresh.vault!.check,
        aad: 'vault:verifier',
      )), verifierPlaintext);
    });

    late String fileId;
    late Uint8List plaintext;

    test('encrypted upload, list, download and decrypt', () async {
      plaintext = Uint8List.fromList(
        utf8.encode('CryptaVault Flutter interoperability ${'x' * 4000}'),
      );
      final enc = await cryptoEncrypt(
        name: 'interop.txt',
        mime: 'text/plain',
        bytes: plaintext,
        profile: 'BALANCED',
      );
      final meta = await sealJson(
        owner.masterKey!,
        enc.meta.toJson(),
        aad: 'filemeta:${enc.container.fileId}',
      );
      final wrapped = await wrapRawKey(
        owner.masterKey!,
        enc.rawKey,
        'filekey:${enc.container.fileId}',
      );
      await owner.api.uploadFile(
        workspaceId: owner.currentWorkspace!.id,
        fileId: enc.container.fileId,
        encryptedMeta: meta.ctB64,
        metaIv: meta.ivB64,
        wrappedKey: wrapped.ctB64,
        wrappedIv: wrapped.ivB64,
        contentTag: '',
        profile: 'BALANCED',
        ciphertext: Uint8List.fromList(
          utf8.encode(jsonEncode(enc.container.toJson())),
        ),
      );
      fileId = enc.container.fileId;

      final files = await owner.api.listFiles(owner.currentWorkspace!.id);
      final listed = files.where((f) => f.id == fileId).toList();
      expect(listed, hasLength(1));
      final metaJson = await openJson(
        owner.masterKey!,
        Sealed(ivB64: listed.first.metaIv, ctB64: listed.first.encryptedMeta),
        aad: 'filemeta:$fileId',
      );
      expect(FileMeta.fromJson(metaJson).name, 'interop.txt');

      final cipher = await owner.api.downloadFile(fileId);
      final container = Container.fromJson(
        Map<String, dynamic>.from(jsonDecode(utf8.decode(cipher)) as Map),
      );
      final rawKey = await unwrapRawKey(
        owner.masterKey!,
        Sealed(ivB64: listed.first.wrappedIv, ctB64: listed.first.wrappedKey),
        'filekey:$fileId',
      );
      final decrypted = await decryptContainer(container, rawKey);
      expect(decrypted, plaintext);
      expect(await sha256Hex(decrypted), FileMeta.fromJson(metaJson).hash);
    });

    test('share with PIN and recipient email, then recipient downloads', () async {
      final share = await owner.api.createShare({
        'file_id': fileId,
        'version': 1,
        'max_uses': 3,
        'recipient_email': recipientEmail,
      });
      expect(share.pin, isNotNull);
      expect(share.pin!.length, 8);
      expect(share.pinProtected, isTrue);

      // Anonymous with the PIN succeeds.
      final anonymous = VaultProvider(MemoryCredentialStore(), baseUrl: 'http://127.0.0.1:8000');
      final bytes = await anonymous.api.downloadShare(share.token, pin: share.pin);
      expect(bytes.isNotEmpty, isTrue);

      // Logged-in recipient bypasses PIN.
      final bypass = await recipient.api.downloadShare(share.token);
      expect(bypass, bytes);

      final received = await recipient.api.receivedShares();
      expect(received.any((s) => s.token == share.token), isTrue);

      // Wrong PIN fails.
      expect(
        () => anonymous.api.downloadShare(share.token, pin: '00000000'),
        throwsA(isA<ApiException>()),
      );

      // Change PIN, then regenerate invalidates the old token.
      final changed = await owner.api.updateSharePin(share.token, pin: '12345678');
      expect(changed.pin, '12345678');
      final regenerated = await owner.api.regenerateShare(share.token);
      expect(regenerated.token, isNot(share.token));
      expect(
        () => anonymous.api.downloadShare(share.token, pin: '12345678'),
        throwsA(isA<ApiException>()),
      );
      await owner.api.revokeShare(regenerated.token);
    });

    test('trash, restore, permanent delete', () async {
      await owner.api.trashFile(fileId);
      var files = await owner.api.listFiles(owner.currentWorkspace!.id);
      expect(files.any((f) => f.id == fileId), isFalse);
      await owner.api.untrashFile(fileId);
      files = await owner.api.listFiles(owner.currentWorkspace!.id);
      expect(files.any((f) => f.id == fileId), isTrue);
      await owner.api.deleteFilePermanent(fileId);
      files = await owner.api.listFiles(owner.currentWorkspace!.id);
      expect(files.any((f) => f.id == fileId), isFalse);
    });
  });
}

/// Thin wrapper so the test uses the same crypto calls as the app screens.
Future<EncryptResult> cryptoEncrypt({
  required String name,
  required String mime,
  required Uint8List bytes,
  required String profile,
}) =>
    encryptFile(
      name: name,
      mime: mime,
      bytes: bytes,
      profile: profile,
      chunkSize: 1024 * 1024,
    );
