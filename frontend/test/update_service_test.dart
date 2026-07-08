import "package:expenis_mobile/service/update_service.dart";
import "package:flutter_test/flutter_test.dart";

void main() {
  group("UpdateService.compareSemver", () {
    test("equal versions return zero", () {
      expect(UpdateService.compareSemver("1.2.3", "1.2.3"), 0);
    });

    test("newer patch returns positive", () {
      expect(UpdateService.compareSemver("1.2.4", "1.2.3"), 1);
    });

    test("older minor returns negative", () {
      expect(UpdateService.compareSemver("1.1.0", "1.2.0"), -1);
    });

    test("major bump dominates minor", () {
      expect(UpdateService.compareSemver("2.0.0", "1.9.9"), 1);
    });

    test("build suffix ignored", () {
      expect(UpdateService.compareSemver("1.0.0+5", "1.0.0"), 0);
    });

    test("pre-release suffix ignored", () {
      expect(UpdateService.compareSemver("1.0.0-rc.1", "1.0.0"), 0);
    });

    test("missing parts treated as zero", () {
      expect(UpdateService.compareSemver("1.0", "1.0.0"), 0);
      expect(UpdateService.compareSemver("2", "1.9.9"), 1);
    });

    test("non-numeric parts treated as zero", () {
      expect(UpdateService.compareSemver("x.y.z", "0.0.0"), 0);
    });
  });
}
