import "package:expenis_mobile/utils/tag_utils.dart";
import "package:flutter_test/flutter_test.dart";

void main() {
  group("matchesTagFilter", () {
    test("passes when no include or exclude is set", () {
      expect(
        matchesTagFilter(["food"], includedKeys: {}, excludedKeys: {}),
        isTrue,
      );
      expect(
        matchesTagFilter(const [], includedKeys: {}, excludedKeys: {}),
        isTrue,
      );
    });

    test("single include keeps only tagged transactions", () {
      expect(
        matchesTagFilter(["food"], includedKeys: {"food"}, excludedKeys: {}),
        isTrue,
      );
      expect(
        matchesTagFilter(["work"], includedKeys: {"food"}, excludedKeys: {}),
        isFalse,
      );
    });

    test("single exclude hides tagged transactions", () {
      expect(
        matchesTagFilter(["work"], includedKeys: {}, excludedKeys: {"work"}),
        isFalse,
      );
      expect(
        matchesTagFilter(["food"], includedKeys: {}, excludedKeys: {"work"}),
        isTrue,
      );
    });

    test("multiple includes match any included tag", () {
      expect(
        matchesTagFilter(
          ["food"],
          includedKeys: {"food", "vacation"},
          excludedKeys: {},
        ),
        isTrue,
      );
      expect(
        matchesTagFilter(
          ["vacation"],
          includedKeys: {"food", "vacation"},
          excludedKeys: {},
        ),
        isTrue,
      );
      expect(
        matchesTagFilter(
          ["work"],
          includedKeys: {"food", "vacation"},
          excludedKeys: {},
        ),
        isFalse,
      );
    });

    test("multiple excludes hide any excluded tag", () {
      expect(
        matchesTagFilter(
          ["food"],
          includedKeys: {},
          excludedKeys: {"food", "work"},
        ),
        isFalse,
      );
      expect(
        matchesTagFilter(
          ["work"],
          includedKeys: {},
          excludedKeys: {"food", "work"},
        ),
        isFalse,
      );
      expect(
        matchesTagFilter(
          ["vacation"],
          includedKeys: {},
          excludedKeys: {"food", "work"},
        ),
        isTrue,
      );
    });

    test("include and exclude together hide overlap", () {
      expect(
        matchesTagFilter(
          ["food"],
          includedKeys: {"food"},
          excludedKeys: {"work"},
        ),
        isTrue,
      );
      expect(
        matchesTagFilter(
          ["food", "work"],
          includedKeys: {"food"},
          excludedKeys: {"work"},
        ),
        isFalse,
      );
      expect(
        matchesTagFilter(
          ["work"],
          includedKeys: {"food"},
          excludedKeys: {"work"},
        ),
        isFalse,
      );
      expect(
        matchesTagFilter(
          ["vacation"],
          includedKeys: {"food"},
          excludedKeys: {"work"},
        ),
        isFalse,
      );
    });

    test("untagged transaction with only excludes is shown", () {
      expect(
        matchesTagFilter(const [], includedKeys: {}, excludedKeys: {"work"}),
        isTrue,
      );
    });

    test("untagged transaction with includes is hidden", () {
      expect(
        matchesTagFilter(const [], includedKeys: {"food"}, excludedKeys: {}),
        isFalse,
      );
    });

    test("compares tags with normalized keys", () {
      expect(
        matchesTagFilter([" Food "], includedKeys: {"food"}, excludedKeys: {}),
        isTrue,
      );
      expect(
        matchesTagFilter(["WORK"], includedKeys: {}, excludedKeys: {"work"}),
        isFalse,
      );
    });
  });
}
