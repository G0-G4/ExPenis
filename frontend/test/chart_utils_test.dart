import "package:flutter_test/flutter_test.dart";

import "package:expenis_mobile/utils/chart_utils.dart";

void main() {
  group("niceAxisScale", () {
    test("rounds bounds and step to nice values", () {
      final scale = niceAxisScale(0, 93500);
      expect(scale.min, 0);
      expect(scale.step, 25000);
      expect(scale.max, 100000);
    });

    test("extends below zero for negative minimum", () {
      final scale = niceAxisScale(-12000, 48000);
      expect(scale.step, 20000);
      expect(scale.min, -20000);
      expect(scale.max, 60000);
    });

    test("falls back to a unit range when there is no data", () {
      final scale = niceAxisScale(0, 0);
      expect(scale.min, 0);
      expect(scale.max, 4);
      expect(scale.step, 1);
    });
  });

  group("compactAmount", () {
    test("formats thousands and millions without trailing .0", () {
      expect(compactAmount(0), "0");
      expect(compactAmount(250), "250");
      expect(compactAmount(1500), "1.5k");
      expect(compactAmount(25000), "25k");
      expect(compactAmount(2000000), "2M");
      expect(compactAmount(-7500), "-7.5k");
    });
  });

  group("labelStride", () {
    test("shows every label when they fit", () {
      expect(labelStride(12, 600, 40), 1);
    });

    test("skips labels when space is tight", () {
      expect(labelStride(12, 300, 40), 2);
      expect(labelStride(24, 300, 40), 4);
    });
  });

  group("topKeysByTotal", () {
    test("returns all keys ranked when within limit plus one", () {
      final keys = topKeysByTotal({"a": 1, "b": 3, "c": 2}, 2);
      expect(keys, ["b", "c", "a"]);
    });

    test("keeps only the largest keys when many remain", () {
      final keys = topKeysByTotal({"a": 1, "b": 5, "c": 4, "d": 2}, 2);
      expect(keys, ["b", "c"]);
    });
  });
}
