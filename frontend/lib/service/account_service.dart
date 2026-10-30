import "package:expenis_mobile/service/telemetry_service.dart";
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
      throw telemetryException(
        'Failed to load accounts with status: ${response.statusCode}',
      );
    } on DioException catch (e) {
      throw telemetryException('Failed to load accounts: ${e.message}');
    } on Object catch (error, stack) {
      TelemetryService.instance.capture(error, stack, code: "client_operation");
      rethrow;
    }
  }

  Future<Account> fetchAccount(int id) async {
    try {
      final response = await dio.get('$baseUrl/api/accounts/account/$id');
      return Account.fromJson(response.data);
    } on DioException catch (e) {
      throw telemetryException('Failed to load account: ${e.message}');
    } on Object catch (error, stack) {
      TelemetryService.instance.capture(error, stack, code: "client_operation");
      rethrow;
    }
  }

  Future<void> updateAccount(Account account) async {
    try {
      await dio.put(
        '$baseUrl/api/accounts/account/${account.id}',
        data: account.toJson(),
      );
    } on DioException catch (e) {
      throw telemetryException('Failed to update account: ${e.message}');
    } on Object catch (error, stack) {
      TelemetryService.instance.capture(error, stack, code: "client_operation");
      rethrow;
    }
  }

  Future<List<String>> fetchCurrencyCodes() async {
    try {
      final response = await dio.get('$baseUrl/api/currency/codes');
      final codesMap = response.data['codes'] as Map<String, dynamic>;
      return codesMap.keys.toList();
    } on DioException catch (e) {
      throw telemetryException('Failed to load currency codes: ${e.message}');
    } on Object catch (error, stack) {
      TelemetryService.instance.capture(error, stack, code: "client_operation");
      rethrow;
    }
  }

  Future<void> deleteAccount(int id) async {
    try {
      await dio.delete('$baseUrl/api/accounts/account/$id');
    } on DioException catch (e) {
      throw telemetryException('Failed to delete account: ${e.message}');
    } on Object catch (error, stack) {
      TelemetryService.instance.capture(error, stack, code: "client_operation");
      rethrow;
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
      throw telemetryException('Failed to create account: ${e.message}');
    } on Object catch (error, stack) {
      TelemetryService.instance.capture(error, stack, code: "client_operation");
      rethrow;
    }
  }
}
