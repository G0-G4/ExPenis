enum CategoryType { income, expense }

class Category {
  final int id;
  final String name;
  final CategoryType type;

  Category({required this.id, required this.name, required this.type});

  factory Category.fromJson(Map<String, dynamic> json) {
    final typeStr = json['type'] as String;
    final CategoryType type;
    switch (typeStr) {
      case 'income':
        type = CategoryType.income;
      case 'expense':
        type = CategoryType.expense;
      default:
        throw ArgumentError('Unknown category type: "$typeStr"');
    }

    return Category(id: json['id'], name: json['name'], type: type);
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'name': name,
    'type': type == CategoryType.income ? 'income' : 'expense',
  };
}
