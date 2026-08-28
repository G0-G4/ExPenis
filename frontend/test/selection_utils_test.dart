import "package:expenis_mobile/utils/selection_utils.dart";
import "package:flutter_test/flutter_test.dart";

void main() {
  group("cycleTagFilter", () {
    test("cycles idle to include to exclude to idle", () {
      var included = <String>{};
      var excluded = <String>{};

      var next = cycleTagFilter(included, excluded, "food");
      expect(next.included, {"food"});
      expect(next.excluded, isEmpty);
      expect(next.included.intersection(next.excluded), isEmpty);

      next = cycleTagFilter(next.included, next.excluded, "food");
      expect(next.included, isEmpty);
      expect(next.excluded, {"food"});
      expect(next.included.intersection(next.excluded), isEmpty);

      next = cycleTagFilter(next.included, next.excluded, "food");
      expect(next.included, isEmpty);
      expect(next.excluded, isEmpty);
      expect(next.included.intersection(next.excluded), isEmpty);
    });

    test("cycles only the tapped key", () {
      final next = cycleTagFilter({"food"}, {"work"}, "vacation");
      expect(next.included, {"food", "vacation"});
      expect(next.excluded, {"work"});
      expect(next.included.intersection(next.excluded), isEmpty);
    });

    test("does not mutate the source sets", () {
      final included = {"food"};
      final excluded = <String>{};
      cycleTagFilter(included, excluded, "food");
      expect(included, {"food"});
      expect(excluded, isEmpty);
    });
  });
}
