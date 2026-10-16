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

  group("category selection", () {
    test("all mode picks up categories new to a period", () {
      expect(effectiveSelection<int>(null, {1, 2}), {1, 2});
      expect(effectiveSelection<int>(null, {1, 2, 3}), {1, 2, 3});
    });

    test("explicit set does not pick up new categories", () {
      final explicit = {1, 2, 3};
      expect(effectiveSelection(explicit, {1, 2, 3, 4}), {1, 2, 3});
    });

    test("deselecting from all mode fixes the remaining set", () {
      final explicit = toggledExplicitSelection<int>(null, {1, 2, 3}, 2);
      expect(explicit, {1, 3});
      expect(effectiveSelection(explicit, {1, 2, 3, 4}), {1, 3});
    });

    test("select all restores all mode and clear all empties", () {
      const Set<int>? selectAll = null;
      expect(effectiveSelection(selectAll, {1, 5}), {1, 5});
      expect(effectiveSelection(<int>{}, {1, 5}), isEmpty);
    });

    test("explicit set survives a period without its categories", () {
      final explicit = {7};
      expect(effectiveSelection(explicit, {1, 2}), isEmpty);
      expect(explicit, {7});
      expect(effectiveSelection(explicit, {7, 8}), {7});
    });
  });
}
