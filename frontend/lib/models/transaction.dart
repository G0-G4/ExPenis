enum TransactionType { income, expense }

class Transaction {
  final int id;
  final String account;
  final TransactionType type;
  final String category;
  final double amount;
  final double amountRubles;
  final String currencyCode;
  final String? description;
  final int accountId;
  final int categoryId;

  Transaction({
    required this.id,
    required this.account,
    required this.type,
    required this.category,
    required this.amount,
    required this.amountRubles,
    required this.currencyCode,
    required this.description,
    required this.accountId,
    required this.categoryId,
  });

  factory Transaction.fromJson(Map<String, dynamic> json) {
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

    return Transaction(
      id: json['id'],
      account: json['account'],
      type: type,
      category: json['category'],
      amount: (json['amount'] as num).toDouble(),
      amountRubles: (json['amount_rubles'] as num).toDouble(),
      currencyCode: json['currency_code'] as String,
      description: json['description'],
      accountId: json['account_id'],
      categoryId: json['category_id'],
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'account': account,
    'type': type == TransactionType.income ? 'income' : 'expense',
    'category': category,
    'amount': amount,
    'amount_rubles': amountRubles,
    'currency_code': currencyCode,
    'description': description,
  };

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is Transaction &&
        other.id == id &&
        other.account == account &&
        other.type == type &&
        other.category == category &&
        other.amount == amount &&
        other.amountRubles == amountRubles &&
        other.currencyCode == currencyCode &&
        other.description == description &&
        other.accountId == accountId &&
        other.categoryId == categoryId;
  }

  @override
  int get hashCode {
    return id.hashCode ^
        account.hashCode ^
        type.hashCode ^
        category.hashCode ^
        amount.hashCode ^
        amountRubles.hashCode ^
        currencyCode.hashCode ^
        description.hashCode ^
        accountId.hashCode ^
        categoryId.hashCode;
  }

  Transaction copyWith({
    int? id,
    String? account,
    TransactionType? type,
    String? category,
    double? amount,
    double? amountRubles,
    String? currencyCode,
    String? description,
    int? accountId,
    int? categoryId,
  }) {
    return Transaction(
      id: id ?? this.id,
      account: account ?? this.account,
      type: type ?? this.type,
      category: category ?? this.category,
      amount: amount ?? this.amount,
      amountRubles: amountRubles ?? this.amountRubles,
      currencyCode: currencyCode ?? this.currencyCode,
      description: description ?? this.description,
      accountId: accountId ?? this.accountId,
      categoryId: categoryId ?? this.categoryId,
    );
  }
}

class TransactionCreateRequest {
  final int accountId;
  final int categoryId;
  final double amount;
  final String? description;
  final DateTime? createdAt;

  TransactionCreateRequest({
    required this.accountId,
    required this.categoryId,
    required this.amount,
    this.description,
    this.createdAt,
  });

  Map<String, dynamic> toJson() => {
    'account_id': accountId,
    'category_id': categoryId,
    'amount': amount,
    'description': description,
    'created_at': createdAt?.toIso8601String(),
  };
}
