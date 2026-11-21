enum AmountExpressionStatus {
  valid,
  empty,
  incomplete,
  invalid,
  divisionByZero,
  limit,
}

class AmountExpressionResult {
  const AmountExpressionResult(this.status, [this.amount]);

  final AmountExpressionStatus status;
  final double? amount;
  bool get isValid => status == AmountExpressionStatus.valid;

  String? get error => switch (status) {
    AmountExpressionStatus.valid => null,
    AmountExpressionStatus.empty => "Please enter an amount",
    AmountExpressionStatus.incomplete => "Please complete the expression",
    AmountExpressionStatus.invalid => "Please enter a valid expression",
    AmountExpressionStatus.divisionByZero => "Cannot divide by zero",
    AmountExpressionStatus.limit =>
      "Expression is too long or amount is too large",
  };
}

AmountExpressionResult evaluateAmountExpression(String text) {
  if (text.length > 512) {
    return const AmountExpressionResult(AmountExpressionStatus.limit);
  }
  if (text.trim().isEmpty) {
    return const AmountExpressionResult(AmountExpressionStatus.empty);
  }
  try {
    final value = _Parser(text).parse();
    final cents = value.cents;
    final decimal = _centsText(cents);
    final amount = double.parse(decimal);
    // Beyond this range a double cannot reliably retain individual cents.
    if (!amount.isFinite || cents.abs() > BigInt.from(4503599627370495)) {
      throw AmountExpressionStatus.limit;
    }
    final roundTrip = _Rational.fromDecimal(amount.toStringAsFixed(2)).cents;
    if (roundTrip != cents) throw AmountExpressionStatus.limit;
    return AmountExpressionResult(
      AmountExpressionStatus.valid,
      amount == 0 ? 0 : amount,
    );
  } on AmountExpressionStatus catch (status) {
    return AmountExpressionResult(status);
  }
}

String _centsText(BigInt cents) {
  final digits = cents.abs().toString().padLeft(3, "0");
  return "${cents.isNegative ? "-" : ""}${digits.substring(0, digits.length - 2)}.${digits.substring(digits.length - 2)}";
}

/// Expand exponent notation so a previously stored number can be edited by
/// the same grammar as newly typed amounts, without rounding it on opening.
String amountExpressionText(double amount) {
  if (!amount.isFinite) return amount.toString();
  final text = amount.toString();
  final parts = text.toLowerCase().split("e");
  if (parts.length == 1) return text;
  final negative = parts[0].startsWith("-");
  final mantissa = parts[0].replaceFirst("-", "");
  final dot = mantissa.indexOf(".");
  final digits = mantissa.replaceAll(".", "");
  final position = (dot < 0 ? mantissa.length : dot) + int.parse(parts[1]);
  final expanded = position <= 0
      ? "0.${"0" * -position}$digits"
      : position >= digits.length
      ? "$digits${"0" * (position - digits.length)}"
      : "${digits.substring(0, position)}.${digits.substring(position)}";
  return "${negative ? "-" : ""}$expanded";
}

class _Rational {
  factory _Rational(BigInt numerator, BigInt denominator) {
    if (denominator == BigInt.zero) throw AmountExpressionStatus.divisionByZero;
    final divisor = numerator.gcd(denominator);
    final sign = denominator.isNegative ? -BigInt.one : BigInt.one;
    return _Rational._(
      numerator ~/ divisor * sign,
      denominator ~/ divisor * sign,
    );
  }
  const _Rational._(this.numerator, this.denominator);

  factory _Rational.fromDecimal(String text) {
    final parts = text.split(".");
    return _Rational(
      BigInt.parse(parts.join()),
      BigInt.from(10).pow(parts.length == 1 ? 0 : parts[1].length),
    );
  }

  final BigInt numerator;
  final BigInt denominator;

  _Rational operator +(_Rational other) => _Rational(
    numerator * other.denominator + other.numerator * denominator,
    denominator * other.denominator,
  );
  _Rational operator -(_Rational other) => this + -other;
  _Rational operator -() => _Rational(-numerator, denominator);
  _Rational operator *(_Rational other) =>
      _Rational(numerator * other.numerator, denominator * other.denominator);
  _Rational operator /(_Rational other) =>
      _Rational(numerator * other.denominator, denominator * other.numerator);

  BigInt get cents {
    final scaled = numerator.abs() * BigInt.from(100);
    var rounded = scaled ~/ denominator;
    if ((scaled % denominator) * BigInt.two >= denominator) {
      rounded += BigInt.one;
    }
    return numerator.isNegative ? -rounded : rounded;
  }
}

class _Parser {
  _Parser(String input)
    : text = input
          .replaceAll(",", ".")
          .replaceAll("×", "*")
          .replaceAll("÷", "/")
          .replaceAll("−", "-");

  final String text;
  int offset = 0;
  int depth = 0;

  String get token {
    while (offset < text.length && text[offset].trim().isEmpty) {
      offset++;
    }
    return offset < text.length ? text[offset] : "";
  }

  bool take(String expected) {
    if (token != expected) return false;
    offset++;
    return true;
  }

  _Rational parse() {
    final value = expression();
    if (token.isNotEmpty) throw AmountExpressionStatus.invalid;
    return value;
  }

  _Rational expression() {
    var value = product();
    while (true) {
      if (take("+")) {
        value = value + product();
      } else if (take("-")) {
        value = value - product();
      } else {
        return value;
      }
    }
  }

  _Rational product() {
    var value = unary();
    while (true) {
      if (take("*")) {
        value = value * unary();
      } else if (take("/")) {
        value = value / unary();
      } else {
        return value;
      }
    }
  }

  _Rational unary() {
    // Iterative signs avoid deep recursion on arbitrary pasted input.
    var negative = false;
    while (true) {
      if (take("-")) {
        negative = !negative;
      } else if (!take("+")) {
        break;
      }
    }
    final value = primary();
    return negative ? -value : value;
  }

  _Rational primary() {
    if (token.isEmpty) throw AmountExpressionStatus.incomplete;
    if (take("(")) {
      if (++depth > 32) throw AmountExpressionStatus.limit;
      final value = expression();
      if (!take(")")) {
        throw token.isEmpty
            ? AmountExpressionStatus.incomplete
            : AmountExpressionStatus.invalid;
      }
      depth--;
      return value;
    }
    final start = offset;
    var digits = 0;
    while (offset < text.length && _isDigit(text[offset])) {
      offset++;
      digits++;
    }
    if (offset < text.length && text[offset] == ".") {
      offset++;
      while (offset < text.length && _isDigit(text[offset])) {
        offset++;
        digits++;
      }
    }
    if (digits == 0) {
      throw token.isEmpty
          ? AmountExpressionStatus.incomplete
          : AmountExpressionStatus.invalid;
    }
    var number = text.substring(start, offset);
    if (number.startsWith(".")) number = "0$number";
    return _Rational.fromDecimal(number);
  }

  bool _isDigit(String char) =>
      char.codeUnitAt(0) >= 48 && char.codeUnitAt(0) <= 57;
}
