import "package:expenis_mobile/models/tag_period.dart";
import "package:expenis_mobile/models/transaction.dart";
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

  group("combinedTagPeriod", () {
    TagPeriod period(String name, DateTime first, DateTime last) => TagPeriod(
      name: name,
      type: TransactionType.expense,
      firstAt: first,
      lastAt: last,
    );

    final periods = [
      period("Trip", DateTime(2024, 3, 5), DateTime(2024, 6, 20)),
      period("repair", DateTime(2025, 1, 10), DateTime(2025, 4, 2)),
    ];

    test("single included tag spans its first to last month", () {
      final result = combinedTagPeriod({"trip"}, periods);
      expect(result?.firstMonth, DateTime(2024, 3, 1));
      expect(result?.lastMonth, DateTime(2024, 6, 1));
    });

    test("two included tags span the union of their months", () {
      final result = combinedTagPeriod({"trip", "repair"}, periods);
      expect(result?.firstMonth, DateTime(2024, 3, 1));
      expect(result?.lastMonth, DateTime(2025, 4, 1));
    });

    test("unknown keys are ignored", () {
      expect(combinedTagPeriod({"missing"}, periods), isNull);
      final result = combinedTagPeriod({"missing", "repair"}, periods);
      expect(result?.firstMonth, DateTime(2025, 1, 1));
    });

    test("no includes yields no period", () {
      expect(combinedTagPeriod({}, periods), isNull);
    });
  });
}
