import 'package:dio/dio.dart';
import 'package:expenis_mobile/models/account.dart';
import 'package:expenis_mobile/service/base_service.dart';

class AccountsResult {
  final List<Account> accounts;
  final double totalAmountRubles;

  const AccountsResult({
    required this.accounts,
    required this.totalAmountRubles,
  });
}

class AccountService extends BaseService {
  Future<AccountsResult> fetchAccounts() async {
    try {
      final response = await dio.get('$baseUrl/api/accounts');

      if (response.statusCode == 200) {
        final accountsMap = response.data['accounts'] as Map<String, dynamic>;
        final accounts = accountsMap.values
            .map((accountJson) => Account.fromJson(accountJson))
            .toList();
        final totalAmountRubles = (response.data['total_amount_rubles'] as num)
            .toDouble();
        return AccountsResult(
          accounts: accounts,
          totalAmountRubles: totalAmountRubles,
        );
      }
      throw Exception(
        'Failed to load accounts with status: ${response.statusCode}',
      );
    } on DioException catch (e) {
      throw Exception('Failed to load accounts: ${e.message}');
    }
  }

  Future<Account> fetchAccount(int id) async {
    try {
      final response = await dio.get('$baseUrl/api/accounts/account/$id');
      return Account.fromJson(response.data);
    } on DioException catch (e) {
      throw Exception('Failed to load account: ${e.message}');
    }
  }

  Future<void> updateAccount(Account account) async {
    try {
      await dio.put(
        '$baseUrl/api/accounts/account/${account.id}',
        data: account.toJson(),
      );
    } on DioException catch (e) {
      throw Exception('Failed to update account: ${e.message}');
    }
  }

  Future<List<String>> fetchCurrencyCodes() async {
    try {
      final response = await dio.get('$baseUrl/api/currency/codes');
      final codesMap = response.data['codes'] as Map<String, dynamic>;
      return codesMap.keys.toList();
    } on DioException catch (e) {
      throw Exception('Failed to load currency codes: ${e.message}');
    }
  }

  Future<void> deleteAccount(int id) async {
    try {
      await dio.delete('$baseUrl/api/accounts/account/$id');
    } on DioException catch (e) {
      throw Exception('Failed to delete account: ${e.message}');
    }
  }

  Future<Account> createAccount(
    String name,
    double amount,
    String currencyCode,
  ) async {
    try {
      final response = await dio.post(
        '$baseUrl/api/accounts/account',
        data: {'name': name, 'amount': amount, 'currency_code': currencyCode},
      );
      return Account.fromJson(response.data);
    } on DioException catch (e) {
      throw Exception('Failed to create account: ${e.message}');
    }
  }
}
