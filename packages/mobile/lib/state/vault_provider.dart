import 'dart:convert';
import 'package:cryptography/cryptography.dart';
import 'package:flutter/foundation.dart';
import '../models/types.dart';
import '../services/api_service.dart';
import '../services/crypto_service.dart';
import '../services/storage_service.dart';

enum VaultStatus { loading, anonymous, locked, unlocked }

class VaultProvider extends ChangeNotifier {
  final CredentialStore storage;
  late final ApiService api;

  VaultStatus status = VaultStatus.loading;
  ApiUser? user;
  ApiVault? vault;
  List<ApiWorkspace> workspaces = [];
  String? currentWorkspaceId;
  SecretKey? masterKey;
  String? lastError;

  VaultProvider(this.storage, {String? baseUrl}) {
    api = ApiService(storage, baseUrl: baseUrl ?? 'https://cryptavault.dhruvmulani.com');
  }

  ApiWorkspace? get currentWorkspace {
    if (workspaces.isEmpty) return null;
    if (currentWorkspaceId != null) {
      for (final w in workspaces) { if (w.id == currentWorkspaceId) return w; }
    }
    return workspaces.first;
  }

  Future<void> init() async {
    final url = await storage.getApiUrl();
    api.baseUrl = url;
    final token = await storage.getToken();
    if (token == null || token.isEmpty) { status = VaultStatus.anonymous; notifyListeners(); return; }
    try {
      final me = await api.me();
      _applyMe(me);
      status = VaultStatus.locked;
    } catch (_) {
      await storage.setToken(null);
      status = VaultStatus.anonymous;
    }
    notifyListeners();
  }

  void _applyMe(Map<String, dynamic> me) {
    user = ApiUser.fromJson(Map<String, dynamic>.from(me['user'] as Map));
    vault = ApiVault.fromJson(Map<String, dynamic>.from(me['vault'] as Map));
    final ws = (me['workspaces'] as List).map((e) => ApiWorkspace.fromJson(Map<String, dynamic>.from(e as Map))).toList();
    workspaces = ws;
  }

  Future<void> refresh() async {
    try {
      final me = await api.me();
      _applyMe(me);
      if (status != VaultStatus.unlocked) status = VaultStatus.locked;
      notifyListeners();
    } catch (_) {
      await logout();
    }
  }

  Future<void> register(String email, String passphrase, String displayName, {String defaultProfile = 'BALANCED'}) async {
    lastError = null;
    final authSalt = randomBytes(16);
    final vaultSalt = randomBytes(16);
    final authKey = await deriveMasterKey(passphrase, authSalt);
    final authKeyBytes = Uint8List.fromList(await authKey.extractBytes());
    final master = await deriveMasterKey(passphrase, vaultSalt);
    final check = await seal(master, Uint8List.fromList(utf8.encode(verifierPlaintext)), aad: 'vault:verifier');
    final res = await api.register({
      'email': email.trim().toLowerCase(),
      'display_name': displayName.trim().isEmpty ? email.split('@').first : displayName.trim(),
      'auth_salt_b64': bytesToB64(authSalt),
      'auth_verifier': bytesToB64(authKeyBytes),
      'vault_salt_b64': bytesToB64(vaultSalt),
      'vault_check': check.toJson(),
      'kdf_iterations': kdfIterations,
    });
    await storage.setToken(res['access_token'] as String);
    _applyMe(res);
    masterKey = master;
    final wsId = await storage.getWorkspaceId();
    currentWorkspaceId = wsId ?? (workspaces.isNotEmpty ? workspaces.first.id : null);
    status = VaultStatus.unlocked;
    notifyListeners();
  }

  Future<void> login(String email, String passphrase) async {
    lastError = null;
    final emailNorm = email.trim().toLowerCase();
    // prelogin to get salt/iterations
    final pre = await _prelogin(emailNorm);
    final authSalt = b64ToBytes(pre['auth_salt_b64'] as String);
    final iters = (pre['kdf_iterations'] ?? kdfIterations) as int;
    final authKey = await deriveMasterKey(passphrase, authSalt, iterations: iters);
    final authKeyBytes = Uint8List.fromList(await authKey.extractBytes());
    final res = await api.login({'email': emailNorm, 'auth_verifier': bytesToB64(authKeyBytes)});
    await storage.setToken(res['access_token'] as String);
    _applyMe(res);
    // derive master
    final v = vault!;
    masterKey = await deriveMasterKey(passphrase, b64ToBytes(v.saltB64), iterations: v.kdfIterations);
    // verify
    final plain = await open(masterKey!, v.check, aad: 'vault:verifier');
    if (utf8.decode(plain) != verifierPlaintext) throw Exception('Vault check failed');
    final wsId = await storage.getWorkspaceId();
    currentWorkspaceId = wsId ?? (workspaces.isNotEmpty ? workspaces.first.id : null);
    status = VaultStatus.unlocked;
    notifyListeners();
  }

  Future<Map<String, dynamic>> _prelogin(String email) => api.prelogin(email);

  Future<void> unlock(String passphrase) async {
    if (vault == null) await refresh();
    final v = vault!;
    final mk = await deriveMasterKey(passphrase, b64ToBytes(v.saltB64), iterations: v.kdfIterations);
    final plain = await open(mk, v.check, aad: 'vault:verifier');
    if (utf8.decode(plain) != verifierPlaintext) throw Exception('Wrong passphrase');
    masterKey = mk;
    status = VaultStatus.unlocked;
    notifyListeners();
  }

  void lock() { masterKey = null; status = VaultStatus.locked; notifyListeners(); }

  Future<void> logout() async {
    await storage.setToken(null);
    masterKey = null; user = null; vault = null; workspaces = []; currentWorkspaceId = null;
    status = VaultStatus.anonymous;
    notifyListeners();
  }

  void selectWorkspace(String id) { currentWorkspaceId = id; storage.setWorkspaceId(id); notifyListeners(); }

  Future<void> setApiUrl(String url) async {
    final u = url.trim().replaceAll(RegExp(r'/+$'), '');
    api.baseUrl = u;
    await storage.setApiUrl(u);
    notifyListeners();
  }
}
