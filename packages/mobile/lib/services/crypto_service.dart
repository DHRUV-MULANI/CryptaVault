import 'dart:convert';
import 'dart:io';
import 'dart:math';
import 'dart:typed_data';
import 'package:cryptography/cryptography.dart';
import '../models/types.dart';

const int kdfIterations = 210000;
const String verifierPlaintext = 'cryptavault:verifier:v1';

final _rng = Random.secure();
final _aesGcm = AesGcm.with256bits();
final _sha256 = Sha256();

Uint8List randomBytes(int length) {
  final b = Uint8List(length);
  for (var i = 0; i < length; i++) { b[i] = _rng.nextInt(256); }
  return b;
}

String bytesToB64(Uint8List bytes) => base64Encode(bytes);
Uint8List b64ToBytes(String value) => Uint8List.fromList(base64Decode(value));

String bytesToB64Url(Uint8List bytes) =>
    base64UrlEncode(bytes).replaceAll('=', '');
Uint8List b64UrlToBytes(String value) {
  var padded = value.replaceAll('-', '+').replaceAll('_', '/');
  padded += '=' * ((4 - padded.length % 4) % 4);
  return Uint8List.fromList(base64Decode(padded));
}

Future<String> sha256Hex(Uint8List bytes) async {
  final hash = await _sha256.hash(bytes);
  return hash.bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
}

Future<SecretKey> deriveMasterKey(String passphrase, Uint8List salt,
    {int iterations = kdfIterations}) async {
  final pbkdf2 = Pbkdf2(
    macAlgorithm: Hmac.sha256(),
    iterations: iterations,
    bits: 256,
  );
  return pbkdf2.deriveKey(secretKey: SecretKey(utf8.encode(passphrase)), nonce: salt);
}

Future<Sealed> seal(SecretKey key, Uint8List plaintext, {String? aad}) async {
  final iv = randomBytes(12);
  final box = await _aesGcm.encrypt(
    plaintext,
    secretKey: key,
    nonce: iv,
    aad: aad != null ? utf8.encode(aad) : const <int>[],
  );
  // WebCrypto format: ciphertext + tag
  final ct = Uint8List(box.cipherText.length + box.mac.bytes.length);
  ct.setAll(0, box.cipherText);
  ct.setAll(box.cipherText.length, box.mac.bytes);
  return Sealed(ivB64: bytesToB64(iv), ctB64: bytesToB64(ct));
}

Future<Uint8List> open(SecretKey key, Sealed sealed, {String? aad}) async {
  final iv = b64ToBytes(sealed.ivB64);
  final ctAll = b64ToBytes(sealed.ctB64);
  if (ctAll.length < 16) throw Exception('Ciphertext too short');
  final cipherText = ctAll.sublist(0, ctAll.length - 16);
  final macBytes = ctAll.sublist(ctAll.length - 16);
  final box = SecretBox(cipherText, nonce: iv, mac: Mac(macBytes));
  final plain = await _aesGcm.decrypt(
    box,
    secretKey: key,
    aad: aad != null ? utf8.encode(aad) : const <int>[],
  );
  return Uint8List.fromList(plain);
}

Future<Sealed> sealJson(SecretKey key, Object value, {String? aad}) =>
    seal(key, Uint8List.fromList(utf8.encode(jsonEncode(value))), aad: aad);

Future<Map<String, dynamic>> openJson(SecretKey key, Sealed sealed, {String? aad}) async {
  final plain = await open(key, sealed, aad: aad);
  return Map<String, dynamic>.from(jsonDecode(utf8.decode(plain)) as Map);
}

Future<SecretKey> importAesKey(Uint8List raw) async => SecretKey(raw);

Future<Sealed> wrapRawKey(SecretKey masterKey, Uint8List raw, String aad) =>
    seal(masterKey, raw, aad: aad);

Future<Uint8List> unwrapRawKey(SecretKey masterKey, Sealed sealed, String aad) =>
    open(masterKey, sealed, aad: aad);

Uint8List generateRawKey() => randomBytes(32);

// CVW1 container
class Container {
  final String magic;
  final int v;
  final String fileId;
  final String createdAt;
  final String profile;
  final String compression;
  final int chunkSize;
  final List<Map<String, dynamic>> chunks;
  Container({required this.magic, required this.v, required this.fileId, required this.createdAt, required this.profile, required this.compression, required this.chunkSize, required this.chunks});
  Map<String, dynamic> toJson() => {'magic': magic, 'v': v, 'fileId': fileId, 'createdAt': createdAt, 'profile': profile, 'compression': compression, 'chunkSize': chunkSize, 'chunks': chunks};
  factory Container.fromJson(Map<String, dynamic> j) => Container(
    magic: j['magic'] as String, v: (j['v'] ?? 1) as int, fileId: j['fileId'] as String,
    createdAt: j['createdAt'] as String, profile: j['profile'] as String,
    compression: j['compression'] as String, chunkSize: (j['chunkSize'] ?? 0) as int,
    chunks: (j['chunks'] as List).map((e) => Map<String, dynamic>.from(e as Map)).toList(),
  );
}

class EncryptResult {
  final Container container;
  final FileMeta meta;
  final Uint8List rawKey;
  EncryptResult({required this.container, required this.meta, required this.rawKey});
}

bool _shouldCompress(String name, String? mime, int size) {
  final t = (mime ?? '').toLowerCase();
  final n = name.toLowerCase();
  const pre = ['image/jpeg','image/png','image/webp','image/gif','video/','audio/','application/zip','application/gzip','application/x-7z','application/pdf'];
  if (pre.any((p) => t.startsWith(p))) return false;
  if (RegExp(r'\.(jpg|jpeg|png|webp|gif|mp4|mkv|mp3|flac|ogg|zip|gz|xz|7z|pdf)$').hasMatch(n)) return false;
  if (t.startsWith('text/') || RegExp(r'\.(txt|md|json|csv|tsv|xml|html|css|js|ts|tsx|jsx|py|rs|go|java|sql|yaml|yml|log)$').hasMatch(n) || size < 512 * 1024) return true;
  return false;
}

Future<EncryptResult> encryptFile({
  required String name,
  required String mime,
  required Uint8List bytes,
  required String profile,
  required int chunkSize,
  bool? compressOverride,
  String? folder,
  void Function(double)? onProgress,
}) async {
  final fileId = _uuid();
  final createdAt = DateTime.now().toUtc().toIso8601String();
  final rawKey = generateRawKey();
  final key = await importAesKey(rawKey);
  final hash = await sha256Hex(bytes);
  final useCompression = compressOverride ?? _shouldCompress(name, mime, bytes.length);
  Uint8List payload = bytes;
  var compression = 'none';
  if (useCompression) {
    try {
      payload = Uint8List.fromList(gzip.encode(bytes));
      compression = 'gzip';
    } catch (_) {
      payload = bytes;
      compression = 'none';
    }
  }
  final chunks = <Map<String, dynamic>>[];
  final total = max(1, (payload.length / chunkSize).ceil());
  for (var i = 0; i < total; i++) {
    final start = i * chunkSize;
    final end = min(start + chunkSize, payload.length);
    final slice = Uint8List.sublistView(payload, start, end);
    final isFinal = i == total - 1 ? 1 : 0;
    final aad = 'cryptavault:web:v1:$fileId:$i:$isFinal';
    final sealed = await seal(key, slice, aad: aad);
    chunks.add({'i': i, 'f': isFinal, 'iv': sealed.ivB64, 'ct': sealed.ctB64});
    onProgress?.call((i + 1) / total);
  }
  final container = Container(magic: 'CVW1', v: 1, fileId: fileId, createdAt: createdAt, profile: profile, compression: compression, chunkSize: chunkSize, chunks: chunks);
  final meta = FileMeta(name: name, type: mime.isEmpty ? 'application/octet-stream' : mime, size: bytes.length, hash: hash, chunkCount: chunks.length, compression: compression, profile: profile, createdAt: createdAt, folder: folder);
  return EncryptResult(container: container, meta: meta, rawKey: rawKey);
}

Future<Uint8List> decryptContainer(Container container, Uint8List rawKey, {void Function(double)? onProgress}) async {
  if (container.magic != 'CVW1' || container.v != 1) throw Exception('Unsupported container format.');
  final key = await importAesKey(rawKey);
  final parts = <Uint8List>[];
  final total = max(1, container.chunks.length);
  for (var idx = 0; idx < container.chunks.length; idx++) {
    final c = container.chunks[idx];
    final i = c['i'] as int; final f = c['f'] as int;
    final aad = 'cryptavault:web:v1:${container.fileId}:$i:$f';
    final plain = await open(key, Sealed(ivB64: c['iv'] as String, ctB64: c['ct'] as String), aad: aad);
    parts.add(plain);
    onProgress?.call((idx + 1) / total);
  }
  final len = parts.fold<int>(0, (s, p) => s + p.length);
  final joined = Uint8List(len);
  var off = 0;
  for (final p in parts) { joined.setAll(off, p); off += p.length; }
  if (container.compression == 'gzip') {
    return Uint8List.fromList(gzip.decode(joined));
  }
  return joined;
}

String _uuid() {
  // simple v4
  final b = randomBytes(16);
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  final h = b.map((x) => x.toRadixString(16).padLeft(2, '0')).join();
  return '${h.substring(0,8)}-${h.substring(8,12)}-${h.substring(12,16)}-${h.substring(16,20)}-${h.substring(20)}';
}
