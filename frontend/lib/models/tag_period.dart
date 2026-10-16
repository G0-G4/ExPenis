import 'package:expenis_mobile/models/transaction.dart';

class TagPeriod {
  final String name;
  final TransactionType type;
  final DateTime firstAt;
  final DateTime lastAt;

  const TagPeriod({
    required this.name,
    required this.type,
    required this.firstAt,
    required this.lastAt,
  });

  factory TagPeriod.fromJson(Map<String, dynamic> json) {
    final typeStr = json['type'] as String;
    final TransactionType type;
    switch (typeStr) {
      case 'income':
        type = TransactionType.income;
      case 'expense':
        type = TransactionType.expense;
      default:
        throw ArgumentError('Unknown transaction type: "$typeStr"');
    }

    return TagPeriod(
      name: json['name'] as String,
      type: type,
      firstAt: DateTime.parse(json['first_at'] as String),
      lastAt: DateTime.parse(json['last_at'] as String),
    );
  }
}
