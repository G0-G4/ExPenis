import "dart:convert";

DateTime? jwtExpiry(String token) {
  try {
    final parts = token.split(".");
    if (parts.length != 3) {
      return null;
    }
    final payload = utf8.decode(
      base64Url.decode(base64Url.normalize(parts[1])),
    );
    final decoded = jsonDecode(payload);
    if (decoded is! Map<String, dynamic>) {
      return null;
    }
    final exp = decoded["exp"];
    if (exp is int) {
      return DateTime.fromMillisecondsSinceEpoch(exp * 1000, isUtc: true);
    }
    if (exp is num) {
      return DateTime.fromMillisecondsSinceEpoch(
        (exp * 1000).round(),
        isUtc: true,
      );
    }
    return null;
  } catch (_) {
    return null;
  }
}

bool jwtIsExpired(String token, {Duration leeway = Duration.zero}) {
  final expiry = jwtExpiry(token);
  if (expiry == null) {
    return true;
  }
  return DateTime.now().toUtc().isAfter(expiry.subtract(leeway));
}
