import 'dart:convert';
import 'dart:typed_data';

import 'package:cryptavault_mobile/services/crypto_service.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('CVW1 crypto', () {
    test('AES-GCM seal/open round-trip with AAD', () async {
      final key = await importAesKey(generateRawKey());
      final sealed = await seal(
        key,
        Uint8List.fromList(utf8.encode('cryptavault:verifier:v1')),
        aad: 'vault:verifier',
      );
      final plain = await open(key, sealed, aad: 'vault:verifier');
      expect(utf8.decode(plain), 'cryptavault:verifier:v1');
    });

    test('wrong AAD fails to decrypt', () async {
      final key = await importAesKey(generateRawKey());
      final sealed = await seal(
        key,
        Uint8List.fromList(utf8.encode('secret')),
        aad: 'filemeta:abc',
      );
      expect(
        () => open(key, sealed, aad: 'filemeta:other'),
        throwsA(anything),
      );
    });

    test('encrypt/decrypt CVW1 container with gzip', () async {
      // Random bytes do not compress, so the chunk count stays predictable.
      final payload = randomBytes(2000);
      final enc = await encryptFile(
        name: 'notes.txt',
        mime: 'text/plain',
        bytes: payload,
        profile: 'BALANCED',
        chunkSize: 512,
      );
      expect(enc.container.magic, 'CVW1');
      expect(enc.container.chunks.length, greaterThan(1));
      expect(enc.meta.hash.length, 64);
      final plain = await decryptContainer(enc.container, enc.rawKey);
      expect(plain, payload);
    });

    test('base64url round-trip', () {
      final raw = randomBytes(32);
      final encoded = bytesToB64Url(raw);
      expect(encoded.contains('='), isFalse);
      expect(b64UrlToBytes(encoded), raw);
    });
  });
}
