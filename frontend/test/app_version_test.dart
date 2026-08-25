import "package:expenis_mobile/utils/app_version.dart";
import "package:flutter_test/flutter_test.dart";

void main() {
  group("parseVersionJson", () {
    test("reads version and build number from a map", () {
      final version = parseVersionJson({
        "app_name": "expenis_mobile",
        "version": "1.0.4",
        "build_number": "5",
        "package_name": "expenis_mobile",
      });
      expect(version, isNotNull);
      expect(version!.version, "1.0.4");
      expect(version.buildNumber, "5");
      expect(version.display, "1.0.4+5");
    });

    test("parses a JSON string", () {
      final version = parseVersionJson(
        '{"version":"1.2.3","build_number":"9"}',
      );
      expect(version?.display, "1.2.3+9");
    });

    test("omits build suffix when build number is missing", () {
      final version = parseVersionJson({"version": "2.0.0"});
      expect(version?.display, "2.0.0");
    });

    test("returns null for invalid payloads", () {
      expect(parseVersionJson(null), isNull);
      expect(parseVersionJson("not-json"), isNull);
      expect(parseVersionJson(<String, dynamic>{}), isNull);
    });
  });
}
