class Account {
  final int id;
  final int userId;
  final String name;
  final double amount;
  final double amountRubles;
  final String currencyCode;

  Account({
    required this.id,
    required this.userId,
    required this.name,
    required this.amount,
    required this.amountRubles,
    required this.currencyCode,
  });

  factory Account.fromJson(Map<String, dynamic> json) {
    return Account(
      id: json['id'],
      userId: json['user_id'],
      name: json['name'],
      amount: (json['amount'] as num).toDouble(),
      amountRubles: (json['amount_rubles'] as num).toDouble(),
      currencyCode: json['currency_code'],
    );
  }

  Map<String, dynamic> toJson() => {
    'name': name,
    'amount': amount,
    'currency_code': currencyCode,
  };

  Account copyWith({
    int? id,
    int? userId,
    String? name,
    double? amount,
    double? amountRubles,
    String? currencyCode,
  }) {
    return Account(
      id: id ?? this.id,
      userId: userId ?? this.userId,
      name: name ?? this.name,
      amount: amount ?? this.amount,
      amountRubles: amountRubles ?? this.amountRubles,
      currencyCode: currencyCode ?? this.currencyCode,
    );
  }
}
