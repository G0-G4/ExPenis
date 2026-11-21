import "package:flutter_test/flutter_test.dart";
import "package:expenis_mobile/utils/amount_expression.dart";

void main() {
  test("arithmetic, decimals, signs and precedence", () {
    final examples = <String, double>{
      "120+80": 200,
      "42.5": 42.5,
      "100+50*2": 200,
      "(100+50)/2": 75,
      "1,5 × 2 + 0.25": 3.25,
      "100/5/2": 10,
      "-100+20": -80,
      "100-100": 0,
      "100/3": 33.33,
      "1/3*3": 1,
      "1.005": 1.01,
      "-1.005": -1.01,
      "-0.001": 0,
      ".5+,5": 1,
      "1.": 1,
      "2*-(-3)": 6,
      "−2÷4": -0.5,
    };
    for (final entry in examples.entries) {
      final result = evaluateAmountExpression(entry.key);
      expect(result.status, AmountExpressionStatus.valid, reason: entry.key);
      expect(result.amount, entry.value, reason: entry.key);
    }
  });

  test("rejects unsupported syntax and consumes all tokens", () {
    for (final text in [
      "10%",
      "2^3",
      "2(3+4)",
      "1 2",
      "1.2.3",
      "()",
      "NaN",
      "Infinity",
      "1e3",
      "1+2)",
    ]) {
      expect(
        evaluateAmountExpression(text).status,
        AmountExpressionStatus.invalid,
        reason: text,
      );
    }
  });

  test("distinguishes empty, incomplete, zero division and limits", () {
    expect(evaluateAmountExpression(" ").status, AmountExpressionStatus.empty);
    for (final text in ["100+", "(1+2", "-", "."]) {
      expect(
        evaluateAmountExpression(text).status,
        AmountExpressionStatus.incomplete,
        reason: text,
      );
    }
    expect(
      evaluateAmountExpression("100/(2-2)").status,
      AmountExpressionStatus.divisionByZero,
    );
    expect(evaluateAmountExpression("1${' ' * 511}").isValid, isTrue);
    expect(
      evaluateAmountExpression("1${' ' * 512}").status,
      AmountExpressionStatus.limit,
    );
    expect(evaluateAmountExpression("${'(' * 32}1${')' * 32}").isValid, isTrue);
    expect(
      evaluateAmountExpression("${'(' * 33}1${')' * 33}").status,
      AmountExpressionStatus.limit,
    );
    expect(
      evaluateAmountExpression("999999999999999999999999.99").status,
      AmountExpressionStatus.limit,
    );
    expect(
      evaluateAmountExpression("${'9' * 250}*${'9' * 250}").status,
      AmountExpressionStatus.limit,
    );
    expect(
      evaluateAmountExpression("45035996273704.91").amount,
      45035996273704.91,
    );
  });

  test(
    "existing numbers expand without exponent notation or early rounding",
    () {
      for (final amount in [1e-7, -1e-7, 1e21, -1e21, 1.005, 200.0]) {
        final text = amountExpressionText(amount);
        expect(text.contains("e"), isFalse);
        expect(double.parse(text), amount);
      }
    },
  );
}
