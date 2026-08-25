import "dart:convert";

import "package:expenis_mobile/utils/jwt.dart";
import "package:flutter_test/flutter_test.dart";

String _unsignedJwt({required int exp}) {
  final header = base64Url.encode(utf8.encode('{"alg":"none","typ":"JWT"}'));
  final payload = base64Url.encode(utf8.encode(jsonEncode({"exp": exp})));
  return "$header.$payload.sig";
}

void main() {
  group("jwtExpiry", () {
    test("reads exp claim as UTC datetime", () {
      final expiry = jwtExpiry(_unsignedJwt(exp: 1700000000));
      expect(expiry, DateTime.utc(2023, 11, 14, 22, 13, 20));
    });

    test("returns null for malformed tokens", () {
      expect(jwtExpiry("not-a-jwt"), isNull);
      expect(jwtExpiry("a.b"), isNull);
    });
  });

  group("jwtIsExpired", () {
    test("expired tokens are expired", () {
      final token = _unsignedJwt(
        exp:
            DateTime.now()
                .toUtc()
                .subtract(const Duration(seconds: 5))
                .millisecondsSinceEpoch ~/
            1000,
      );
      expect(jwtIsExpired(token), isTrue);
    });

    test("future tokens are not expired", () {
      final token = _unsignedJwt(
        exp:
            DateTime.now()
                .toUtc()
                .add(const Duration(hours: 1))
                .millisecondsSinceEpoch ~/
            1000,
      );
      expect(jwtIsExpired(token), isFalse);
    });

    test("undecodable tokens are treated as expired", () {
      expect(jwtIsExpired("broken"), isTrue);
    });
  });
}
