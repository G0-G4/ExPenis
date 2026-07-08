import 'package:dio/dio.dart';
import 'package:expenis_mobile/models/transaction.dart';
import 'package:expenis_mobile/service/base_service.dart';

class TransactionService extends BaseService {
  Future<List<String>> fetchTags() async {
    try {
      final response = await dio.get('$baseUrl/api/tags');
      if (response.statusCode == 200) {
        return (response.data['tags'] as List<dynamic>)
            .map((tag) => tag as String)
            .toList();
      }
      throw Exception(
        'Failed to load tags with status: ${response.statusCode}',
      );
    } on DioException catch (e) {
      throw Exception('Failed to load tags: ${e.message}');
    }
  }

  String _formatDate(DateTime date) {
    final month = date.month.toString().padLeft(2, '0');
    final day = date.day.toString().padLeft(2, '0');
    return '${date.year}-$month-$day';
  }

  Future<List<Transaction>> fetchTransactions({
    required DateTime dateFrom,
    required DateTime dateTo,
  }) async {
    try {
      final response = await dio.get(
        '$baseUrl/api/transactions',
        queryParameters: {
          'date_from': _formatDate(dateFrom),
          'date_to': _formatDate(dateTo),
        },
      );

      if (response.statusCode == 200) {
        return (response.data['transactions'] as List)
            .map((json) => Transaction.fromJson(json))
            .toList();
      }
      throw Exception(
        'Failed to load transactions with status: ${response.statusCode}',
      );
    } on DioException catch (e) {
      throw Exception('Failed to load transactions: ${e.message}');
    }
  }

  Future<Transaction> fetchTransaction(int id) async {
    try {
      final response = await dio.get('$baseUrl/api/transactions/$id');
      return Transaction.fromJson(response.data);
    } on DioException catch (e) {
      throw Exception('Failed to load transaction: ${e.message}');
    }
  }

  Future<Transaction> createTransaction(
    TransactionCreateRequest request,
  ) async {
    try {
      final response = await dio.post(
        '$baseUrl/api/transactions',
        data: request.toJson(),
      );
      return Transaction.fromJson(response.data);
    } on DioException catch (e) {
      throw Exception('Failed to create transaction: ${e.message}');
    }
  }

  Future<void> updateTransaction(
    int transactionId,
    TransactionCreateRequest request,
  ) async {
    try {
      await dio.put(
        '$baseUrl/api/transactions/$transactionId',
        data: request.toJson(),
      );
    } on DioException catch (e) {
      throw Exception('Failed to update transaction: ${e.message}');
    }
  }

  Future<void> deleteTransaction(int id) async {
    try {
      await dio.delete('$baseUrl/api/transactions/$id');
    } on DioException catch (e) {
      throw Exception('Failed to delete transaction: ${e.message}');
    }
  }
}
