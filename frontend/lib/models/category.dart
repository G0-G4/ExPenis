import "package:flutter/material.dart";

import "package:expenis_mobile/utils/category_colors.dart";

enum CategoryType { income, expense }

class Category {
  final int id;
  final String name;
  final CategoryType type;
  final String color;

  const Category({
    required this.id,
    required this.name,
    required this.type,
    required this.color,
  });

  Color get displayColor => categoryDisplayColor(color);

  factory Category.fromJson(Map<String, dynamic> json) {
    final type = switch (json["type"]) {
      "income" => CategoryType.income,
      "expense" => CategoryType.expense,
      final value => throw ArgumentError("Unknown category type: $value"),
    };
    return Category(
      id: json["id"],
      name: json["name"],
      type: type,
      color: json["color"] as String,
    );
  }

  Map<String, dynamic> toJson() => {
    "id": id,
    "name": name,
    "type": type.name,
    "color": color,
  };
}
