import '../models/types.dart';

class ServerShareLink {
  final String token;
  final String? keyB64Url;
  final String? name;
  final String? type;
  final int? size;
  final String? hash;

  const ServerShareLink({
    required this.token,
    this.keyB64Url,
    this.name,
    this.type,
    this.size,
    this.hash,
  });
}

String buildServerShareLink(String shareUrl, String keyB64Url, FileMeta meta) {
  final base = shareUrl.trim().isEmpty ? '#/s/' : shareUrl.trim();
  final uri = Uri.parse(base);
  final params = <String, String>{
    'k': keyB64Url,
    if (meta.name.isNotEmpty) 'n': meta.name,
    if (meta.type.isNotEmpty) 't': meta.type,
    if (meta.size > 0) 's': '${meta.size}',
    if (meta.hash.isNotEmpty) 'h': meta.hash,
  };
  return uri.replace(query: Uri(queryParameters: params).query).toString();
}

ServerShareLink parseServerShareLink(String raw) {
  final text = raw.trim();
  final uri = Uri.tryParse(text);

  if (uri != null &&
      (uri.fragment.startsWith('/s/') || uri.pathSegments.contains('s'))) {
    late final String token;
    late final Map<String, String> params;

    if (uri.fragment.startsWith('/s/')) {
      final fragment = uri.fragment;
      final queryIndex = fragment.indexOf('?');
      final path = queryIndex >= 0
          ? fragment.substring(0, queryIndex)
          : fragment;
      final query = queryIndex >= 0 ? fragment.substring(queryIndex + 1) : '';
      token = path.split('/').last;
      params = Uri.splitQueryString(query);
    } else {
      final index = uri.pathSegments.indexOf('s');
      token = uri.pathSegments[index + 1];
      params = uri.queryParameters;
    }

    return ServerShareLink(
      token: token,
      keyB64Url: params['k'],
      name: params['n'],
      type: params['t'],
      size: int.tryParse(params['s'] ?? ''),
      hash: params['h'],
    );
  }

  return ServerShareLink(token: text);
}

String safeShareFileName(String name) {
  final cleaned = name.replaceAll(RegExp(r'[\\/\u0000-\u001f]'), '_').trim();
  return cleaned.isEmpty ? 'cryptavault-shared' : cleaned;
}
