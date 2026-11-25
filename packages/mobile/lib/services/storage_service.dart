import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Abstraction over the small amount of client state the API client needs.
/// Kept separate from Flutter secure storage so tests can supply memory storage.
abstract class CredentialStore {
  Future<String?> getToken();
  Future<void> setToken(String? value);
  Future<String?> getWorkspaceId();
  Future<void> setWorkspaceId(String? value);
  Future<String> getApiUrl();
  Future<void> setApiUrl(String value);
}

class StorageService implements CredentialStore {
  static const _storage = FlutterSecureStorage();
  static const _tokenKey = 'cv_token';
  static const _wsKey = 'cv_workspace';
  static const _apiUrlKey = 'cv_api_url';

  @override
  Future<String?> getToken() => _storage.read(key: _tokenKey);

  @override
  Future<void> setToken(String? v) async {
    if (v == null) {
      await _storage.delete(key: _tokenKey);
    } else {
      await _storage.write(key: _tokenKey, value: v);
    }
  }

  @override
  Future<String?> getWorkspaceId() => _storage.read(key: _wsKey);

  @override
  Future<void> setWorkspaceId(String? v) async {
    if (v == null) {
      await _storage.delete(key: _wsKey);
    } else {
      await _storage.write(key: _wsKey, value: v);
    }
  }

  @override
  Future<String> getApiUrl() async =>
      (await _storage.read(key: _apiUrlKey)) ?? 'https://cryptavault.dhruvmulani.com';

  @override
  Future<void> setApiUrl(String v) => _storage.write(key: _apiUrlKey, value: v);
}

/// In-memory implementation used by tests and interop checks. Never holds keys.
class MemoryCredentialStore implements CredentialStore {
  String? _token;
  String? _workspaceId;
  String _apiUrl = 'http://127.0.0.1:8000';

  @override
  Future<String?> getToken() async => _token;

  @override
  Future<void> setToken(String? value) async => _token = value;

  @override
  Future<String?> getWorkspaceId() async => _workspaceId;

  @override
  Future<void> setWorkspaceId(String? value) async => _workspaceId = value;

  @override
  Future<String> getApiUrl() async => _apiUrl;

  @override
  Future<void> setApiUrl(String value) async => _apiUrl = value;
}
