class Sealed {
  final String ivB64;
  final String ctB64;
  const Sealed({required this.ivB64, required this.ctB64});
  factory Sealed.fromJson(Map<String, dynamic> j) => Sealed(ivB64: j['ivB64'] as String, ctB64: j['ctB64'] as String);
  Map<String, dynamic> toJson() => {'ivB64': ivB64, 'ctB64': ctB64};
}

class ApiUser {
  final String id;
  final String email;
  final String displayName;
  final String role;
  final bool suspended;
  final int quotaBytes;
  final int usedBytes;
  final String defaultProfile;
  ApiUser({required this.id, required this.email, required this.displayName, required this.role, required this.suspended, required this.quotaBytes, required this.usedBytes, required this.defaultProfile});
  factory ApiUser.fromJson(Map<String, dynamic> j) => ApiUser(
    id: j['id'] as String, email: j['email'] as String,
    displayName: (j['display_name'] ?? '') as String,
    role: (j['role'] ?? 'user') as String,
    suspended: j['suspended'] == true,
    quotaBytes: (j['quota_bytes'] ?? 0) as int,
    usedBytes: (j['used_bytes'] ?? 0) as int,
    defaultProfile: (j['default_profile'] ?? 'BALANCED') as String,
  );
}

class ApiVault {
  final String saltB64;
  final int kdfIterations;
  final Sealed check;
  ApiVault({required this.saltB64, required this.kdfIterations, required this.check});
  factory ApiVault.fromJson(Map<String, dynamic> j) => ApiVault(
    saltB64: j['salt_b64'] as String,
    kdfIterations: (j['kdf_iterations'] ?? 210000) as int,
    check: Sealed.fromJson(Map<String, dynamic>.from(j['check'] as Map)),
  );
}

class ApiWorkspace {
  final String id;
  final String name;
  final String role;
  final String defaultProfile;
  ApiWorkspace({required this.id, required this.name, required this.role, required this.defaultProfile});
  factory ApiWorkspace.fromJson(Map<String, dynamic> j) => ApiWorkspace(
    id: j['id'] as String, name: j['name'] as String,
    role: (j['role'] ?? 'viewer') as String,
    defaultProfile: (j['default_profile'] ?? 'BALANCED') as String,
  );
}

class ApiFile {
  final String id;
  final String workspaceId;
  final int currentVersion;
  final String? deletedAt;
  final String encryptedMeta;
  final String metaIv;
  final String wrappedKey;
  final String wrappedIv;
  final int ciphertextSize;
  final String contentTag;
  final String profile;
  ApiFile({required this.id, required this.workspaceId, required this.currentVersion, this.deletedAt, required this.encryptedMeta, required this.metaIv, required this.wrappedKey, required this.wrappedIv, required this.ciphertextSize, required this.contentTag, required this.profile});
  factory ApiFile.fromJson(Map<String, dynamic> j) => ApiFile(
    id: j['id'] as String, workspaceId: j['workspace_id'] as String,
    currentVersion: (j['current_version'] ?? 1) as int,
    deletedAt: j['deleted_at'] as String?,
    encryptedMeta: j['encrypted_meta'] as String, metaIv: j['meta_iv'] as String,
    wrappedKey: j['wrapped_key'] as String, wrappedIv: j['wrapped_iv'] as String,
    ciphertextSize: (j['ciphertext_size'] ?? 0) as int,
    contentTag: (j['content_tag'] ?? '') as String,
    profile: (j['profile'] ?? 'BALANCED') as String,
  );
}

class FileMeta {
  final String name;
  final String type;
  final int size;
  final String hash;
  final int chunkCount;
  final String compression;
  final String profile;
  final String createdAt;
  final String? folder;
  FileMeta({required this.name, required this.type, required this.size, required this.hash, required this.chunkCount, required this.compression, required this.profile, required this.createdAt, this.folder});
  factory FileMeta.fromJson(Map<String, dynamic> j) => FileMeta(
    name: j['name'] as String, type: (j['type'] ?? 'application/octet-stream') as String,
    size: (j['size'] ?? 0) as int, hash: (j['hash'] ?? '') as String,
    chunkCount: (j['chunkCount'] ?? j['chunk_count'] ?? 0) as int,
    compression: (j['compression'] ?? 'none') as String,
    profile: (j['profile'] ?? 'BALANCED') as String,
    createdAt: (j['createdAt'] ?? j['created_at'] ?? '') as String,
    folder: j['folder'] as String?,
  );
  Map<String, dynamic> toJson() => {'name': name, 'type': type, 'size': size, 'hash': hash, 'chunkCount': chunkCount, 'compression': compression, 'profile': profile, 'createdAt': createdAt, if (folder != null) 'folder': folder};
}

class ApiShare {
  final String token;
  final String fileId;
  final int version;
  final String shareUrl;
  final String? recipientEmail;
  final String? createdAt;
  final String? expiresAt;
  final int maxUses;
  final int uses;
  final int remainingUses;
  final bool passwordProtected;
  final bool pinProtected;
  final bool revoked;
  final String? pin;
  ApiShare({required this.token, required this.fileId, required this.version, required this.shareUrl, this.recipientEmail, this.createdAt, this.expiresAt, required this.maxUses, required this.uses, required this.remainingUses, required this.passwordProtected, required this.pinProtected, required this.revoked, this.pin});
  factory ApiShare.fromJson(Map<String, dynamic> j) => ApiShare(
    token: j['token'] as String, fileId: j['file_id'] as String, version: (j['version'] ?? 1) as int,
    shareUrl: (j['share_url'] ?? '') as String, recipientEmail: j['recipient_email'] as String?,
    createdAt: j['created_at'] as String?, expiresAt: j['expires_at'] as String?,
    maxUses: (j['max_uses'] ?? 1) as int, uses: (j['uses'] ?? 0) as int,
    remainingUses: (j['remaining_uses'] ?? 0) as int,
    passwordProtected: j['password_protected'] == true, pinProtected: j['pin_protected'] == true,
    revoked: j['revoked'] == true, pin: j['pin'] as String?,
  );
}
