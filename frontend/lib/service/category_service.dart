import 'package:dio/dio.dart';
import 'package:expenis_mobile/models/category.dart';
import 'package:expenis_mobile/service/base_service.dart';

class CategoryService extends BaseService {
  Future<List<Category>> fetchCategories() async {
    try {
      final response = await dio.get('$baseUrl/api/categories');
      if (response.statusCode == 200) {
        final categoriesMap =
            response.data['categories'] as Map<String, dynamic>;
        return categoriesMap.values
            .map((catJson) => Category.fromJson(catJson))
            .toList();
      }
      throw Exception(
        'Failed to load categories with status: ${response.statusCode}',
      );
    } on DioException catch (e) {
      throw Exception('Failed to load categories: ${e.message}');
    }
  }

  Future<Category> fetchCategory(int id) async {
    try {
      final response = await dio.get('$baseUrl/api/categories/$id');
      return Category.fromJson(response.data);
    } on DioException catch (e) {
      throw Exception('Failed to load category: ${e.message}');
    }
  }

  Future<void> updateCategory(Category category) async {
    try {
      await dio.put(
        '$baseUrl/api/categories/${category.id}',
        data: category.toJson(),
      );
    } on DioException catch (e) {
      throw Exception('Failed to update category: ${e.message}');
    }
  }

  Future<void> deleteCategory(int id) async {
    try {
      await dio.delete('$baseUrl/api/categories/$id');
    } on DioException catch (e) {
      throw Exception('Failed to delete category: ${e.message}');
    }
  }

  Future<Category> createCategory(String name, CategoryType type) async {
    try {
      final response = await dio.post(
        '$baseUrl/api/categories',
        data: {
          'name': name,
          'type': type == CategoryType.income ? 'income' : 'expense',
        },
      );
      return Category.fromJson(response.data);
    } on DioException catch (e) {
      throw Exception('Failed to create category: ${e.message}');
    }
  }
}
