import 'dart:convert';
import 'dart:typed_data';
import 'package:http/http.dart' as http;
import '../models/types.dart';
import 'storage_service.dart';

class ApiException implements Exception {
  final int status;
  final String message;
  final dynamic body;
  ApiException(this.status, this.message, [this.body]);
  @override
  String toString() => message;
}

class ApiService {
  final CredentialStore storage;
  String baseUrl;
  ApiService(this.storage, {this.baseUrl = 'https://cryptavault.dhruvmulani.com'});

  Future<Map<String, String>> _headers({bool json = true}) async {
    final h = <String, String>{};
    if (json) h['Content-Type'] = 'application/json';
    final t = await storage.getToken();
    if (t != null && t.isNotEmpty) h['Authorization'] = 'Bearer $t';
    return h;
  }

  Uri _u(String path) => Uri.parse('$baseUrl$path');

  dynamic _decode(http.Response r) {
    final body = r.body.isEmpty ? null : jsonDecode(r.body);
    if (r.statusCode >= 400) {
      final msg = body is Map && body['detail'] != null ? body['detail'].toString() : 'Request failed (${r.statusCode})';
      throw ApiException(r.statusCode, msg, body);
    }
    return body;
  }

  // Auth
  Future<Map<String, dynamic>> prelogin(String email) async {
    final r = await http.post(_u('/api/auth/prelogin'), headers: await _headers(), body: jsonEncode({'email': email}));
    return Map<String, dynamic>.from(_decode(r) as Map);
  }
  Future<Map<String, dynamic>> register(Map<String, dynamic> payload) async {
    final r = await http.post(_u('/api/auth/register'), headers: await _headers(), body: jsonEncode(payload));
    return Map<String, dynamic>.from(_decode(r) as Map);
  }
  Future<Map<String, dynamic>> login(Map<String, dynamic> payload) async {
    final r = await http.post(_u('/api/auth/login'), headers: await _headers(), body: jsonEncode(payload));
    return Map<String, dynamic>.from(_decode(r) as Map);
  }
  Future<Map<String, dynamic>> me() async {
    final r = await http.get(_u('/api/auth/me'), headers: await _headers());
    return Map<String, dynamic>.from(_decode(r) as Map);
  }

  // Workspaces
  Future<List<ApiWorkspace>> listWorkspaces() async {
    final r = await http.get(_u('/api/workspaces'), headers: await _headers());
    final list = _decode(r) as List;
    return list.map((e) => ApiWorkspace.fromJson(Map<String, dynamic>.from(e as Map))).toList();
  }
  Future<ApiWorkspace> createWorkspace(String name, {String defaultProfile = 'BALANCED'}) async {
    final r = await http.post(_u('/api/workspaces'), headers: await _headers(), body: jsonEncode({'name': name, 'default_profile': defaultProfile}));
    return ApiWorkspace.fromJson(Map<String, dynamic>.from(_decode(r) as Map));
  }

  // Files
  Future<List<ApiFile>> listFiles(String workspaceId, {bool includeDeleted = false}) async {
    final r = await http.get(_u('/api/workspaces/$workspaceId/files?include_deleted=$includeDeleted'), headers: await _headers());
    final list = _decode(r) as List;
    return list.map((e) => ApiFile.fromJson(Map<String, dynamic>.from(e as Map))).toList();
  }

  Future<void> uploadFile({
    required String workspaceId,
    required String fileId,
    required String encryptedMeta,
    required String metaIv,
    required String wrappedKey,
    required String wrappedIv,
    required String contentTag,
    required String profile,
    required Uint8List ciphertext,
  }) async {
    final req = http.MultipartRequest('POST', _u('/api/workspaces/$workspaceId/files/upload'));
    final t = await storage.getToken();
    if (t != null) req.headers['Authorization'] = 'Bearer $t';
    req.fields.addAll({
      'file_id': fileId, 'version': '1', 'encrypted_meta': encryptedMeta, 'meta_iv': metaIv,
      'wrapped_key': wrappedKey, 'wrapped_iv': wrappedIv, 'content_tag': contentTag, 'profile': profile,
    });
    req.files.add(http.MultipartFile.fromBytes('ciphertext', ciphertext, filename: '$fileId.cv'));
    final streamed = await req.send();
    final r = await http.Response.fromStream(streamed);
    _decode(r);
  }

  Future<Uint8List> downloadFile(String fileId) async {
    final r = await http.get(_u('/api/files/$fileId/download'), headers: await _headers(json: false));
    if (r.statusCode >= 400) throw ApiException(r.statusCode, 'Download failed (${r.statusCode})');
    return r.bodyBytes;
  }

  Future<void> trashFile(String fileId) async { _decode(await http.delete(_u('/api/files/$fileId'), headers: await _headers())); }
  Future<void> untrashFile(String fileId) async { _decode(await http.post(_u('/api/files/$fileId/untrash'), headers: await _headers())); }
  Future<void> deleteFilePermanent(String fileId) async { _decode(await http.delete(_u('/api/files/$fileId/permanent'), headers: await _headers())); }

  // Shares
  Future<List<ApiShare>> listShares() async {
    final r = await http.get(_u('/api/shares'), headers: await _headers());
    return (_decode(r) as List).map((e) => ApiShare.fromJson(Map<String, dynamic>.from(e as Map))).toList();
  }
  Future<List<ApiShare>> receivedShares() async {
    final r = await http.get(_u('/api/shares/received'), headers: await _headers());
    return (_decode(r) as List).map((e) => ApiShare.fromJson(Map<String, dynamic>.from(e as Map))).toList();
  }
  Future<ApiShare> createShare(Map<String, dynamic> payload) async {
    final r = await http.post(_u('/api/shares'), headers: await _headers(), body: jsonEncode(payload));
    return ApiShare.fromJson(Map<String, dynamic>.from(_decode(r) as Map));
  }
  Future<Map<String, dynamic>> shareInfo(String token) async {
    final r = await http.get(_u('/api/shares/$token'), headers: await _headers());
    return Map<String, dynamic>.from(_decode(r) as Map);
  }
  Future<Uint8List> downloadShare(String token, {String? password, String? pin}) async {
    final r = await http.post(_u('/api/shares/$token/download'), headers: await _headers(), body: jsonEncode({'password': ?password, 'pin': ?pin}));
    if (r.statusCode >= 400) {
      final body = r.body.isEmpty ? null : jsonDecode(r.body);
      final msg = body is Map && body['detail'] != null ? body['detail'].toString() : 'Download failed';
      throw ApiException(r.statusCode, msg, body);
    }
    return r.bodyBytes;
  }
  Future<ApiShare> updateSharePin(String token, {String? pin}) async {
    final r = await http.patch(_u('/api/shares/$token/pin'), headers: await _headers(), body: jsonEncode({'pin': pin}));
    return ApiShare.fromJson(Map<String, dynamic>.from(_decode(r) as Map));
  }
  Future<ApiShare> regenerateShare(String token) async {
    final r = await http.post(_u('/api/shares/$token/regenerate'), headers: await _headers());
    return ApiShare.fromJson(Map<String, dynamic>.from(_decode(r) as Map));
  }
  Future<void> revokeShare(String token) async { _decode(await http.delete(_u('/api/shares/$token'), headers: await _headers())); }

  // Dashboard / status / admin
  Future<Map<String, dynamic>> dashboard() async {
    final r = await http.get(_u('/api/dashboard'), headers: await _headers());
    return Map<String, dynamic>.from(_decode(r) as Map);
  }

  Future<Map<String, dynamic>> adminDashboard() async {
    final r = await http.get(_u('/api/dashboard/admin'), headers: await _headers());
    return Map<String, dynamic>.from(_decode(r) as Map);
  }

  Future<List<ApiUser>> adminUsers() async {
    final r = await http.get(_u('/api/admin/users'), headers: await _headers());
    return (_decode(r) as List)
        .map((e) => ApiUser.fromJson(Map<String, dynamic>.from(e as Map)))
        .toList();
  }

  Future<Map<String, dynamic>> adminUpdateUser(
    String userId,
    Map<String, dynamic> payload,
  ) async {
    final r = await http.patch(
      _u('/api/admin/users/$userId'),
      headers: await _headers(),
      body: jsonEncode(payload),
    );
    return Map<String, dynamic>.from(_decode(r) as Map);
  }

  Future<Map<String, bool>> adminFlags() async {
    final r = await http.get(_u('/api/admin/flags'), headers: await _headers());
    return (_decode(r) as Map).map(
      (k, v) => MapEntry(k.toString(), v == true),
    );
  }

  Future<void> adminSetFlag(String name, bool enabled) async {
    _decode(await http.put(
      _u('/api/admin/flags/$name'),
      headers: await _headers(),
      body: jsonEncode({'enabled': enabled}),
    ));
  }

  Future<Map<String, dynamic>> adminHealth() async {
    final r = await http.get(_u('/api/admin/health'), headers: await _headers());
    return Map<String, dynamic>.from(_decode(r) as Map);
  }
}
