import 'package:intl/intl.dart';

/// Formats a monetary [amount] with space thousands separators and a dot
/// decimal separator.
///
/// Whole numbers are shown without decimal places; fractional values are
/// rounded to 2 decimal places.
///
/// Examples:
///   formatAmount(1000)        → '1 000'
///   formatAmount(1000000.12)  → '1 000 000.12'
///   formatAmount(500)         → '500'
///   formatAmount(0.5)         → '0.50'
String formatAmount(double amount) {
  final isWhole = amount == amount.truncateToDouble();
  final pattern = isWhole ? '#,##0' : '#,##0.00';
  // en_US gives comma thousands + dot decimal; we then swap commas to spaces.
  final formatted = NumberFormat(pattern, 'en_US').format(amount);
  return formatted.replaceAll(',', '\u00a0');
}
