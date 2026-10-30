import "package:expenis_mobile/service/telemetry_service.dart";
import 'package:dio/dio.dart';
import 'package:expenis_mobile/service/base_service.dart';

class AuthSession {
  final String accessToken;
  final String refreshToken;
  final int expiresIn;

  const AuthSession({
    required this.accessToken,
    required this.refreshToken,
    required this.expiresIn,
  });

  factory AuthSession.fromJson(Map<String, dynamic> json) {
    return AuthSession(
      accessToken: json["access_token"] as String,
      refreshToken: json["refresh_token"] as String,
      expiresIn: (json["expires_in"] as num).toInt(),
    );
  }
}

class UserProfile {
  final int id;
  final String? username;
  final int? telegramId;

  const UserProfile({
    required this.id,
    required this.username,
    required this.telegramId,
  });

  factory UserProfile.fromJson(Map<String, dynamic> json) {
    return UserProfile(
      id: (json["id"] as num).toInt(),
      username: json["username"] as String?,
      telegramId: json["telegram_id"] == null
          ? null
          : (json["telegram_id"] as num).toInt(),
    );
  }
}

class AuthService extends BaseService {
  Future<AuthSession> login(String username, String password) async {
    try {
      final response = await dio.post(
        "$baseUrl/api/login",
        data: {"username": username, "password": password},
        options: Options(extra: {"skipAuth": true}),
      );
      if (response.statusCode == 200 || response.statusCode == 201) {
        return AuthSession.fromJson(response.data as Map<String, dynamic>);
      }
      if (response.statusCode == 401) {
        throw telemetryException("Invalid username or password");
      }
      throw telemetryException(
        "Login failed with status ${response.statusCode}: ${response.data}",
      );
    } on DioException catch (e) {
      throw telemetryException("Login request failed: ${e.message}");
    } on Object catch (error, stack) {
      TelemetryService.instance.capture(error, stack, code: "client_operation");
      rethrow;
    }
  }

  Future<AuthSession> register(String username, String password) async {
    try {
      final response = await dio.post(
        "$baseUrl/api/register",
        data: {"username": username, "password": password},
        options: Options(extra: {"skipAuth": true}),
      );
      if (response.statusCode == 200 || response.statusCode == 201) {
        return AuthSession.fromJson(response.data as Map<String, dynamic>);
      }
      if (response.statusCode == 409) {
        throw telemetryException("Username is already taken");
      }
      if (response.statusCode == 422) {
        throw telemetryException("Invalid input: ${response.data}");
      }
      throw telemetryException(
        "Registration failed with status ${response.statusCode}: ${response.data}",
      );
    } on DioException catch (e) {
      throw telemetryException("Registration request failed: ${e.message}");
    } on Object catch (error, stack) {
      TelemetryService.instance.capture(error, stack, code: "client_operation");
      rethrow;
    }
  }

  Future<AuthSession> refresh(String refreshToken) async {
    try {
      final response = await dio.post(
        "$baseUrl/api/refresh",
        options: Options(
          headers: {"Authorization": "Bearer $refreshToken"},
          extra: {"skipAuth": true},
        ),
      );
      if (response.statusCode == 200 || response.statusCode == 201) {
        return AuthSession.fromJson(response.data as Map<String, dynamic>);
      }
      throw telemetryException(
        "Token refresh failed with status ${response.statusCode}",
      );
    } on DioException catch (e) {
      throw telemetryException("Token refresh request failed: ${e.message}");
    } on Object catch (error, stack) {
      TelemetryService.instance.capture(error, stack, code: "client_operation");
      rethrow;
    }
  }

  Future<void> logout(String accessToken) async {
    try {
      await dio.post(
        "$baseUrl/api/logout",
        options: Options(
          headers: {"Authorization": "Bearer $accessToken"},
          extra: {"skipAuth": true},
        ),
      );
    } on DioException catch (e) {
      throw telemetryException("Logout request failed: ${e.message}");
    } on Object catch (error, stack) {
      TelemetryService.instance.capture(error, stack, code: "client_operation");
      rethrow;
    }
  }

  Future<UserProfile> me([String? accessToken]) async {
    try {
      final response = await dio.get(
        "$baseUrl/api/me",
        options: accessToken == null
            ? null
            : Options(headers: {"Authorization": "Bearer $accessToken"}),
      );
      if (response.statusCode == 200) {
        return UserProfile.fromJson(response.data as Map<String, dynamic>);
      }
      throw telemetryException(
        "Failed to load profile with status ${response.statusCode}",
      );
    } on DioException catch (e) {
      throw telemetryException("Failed to load profile: ${e.message}");
    } on Object catch (error, stack) {
      TelemetryService.instance.capture(error, stack, code: "client_operation");
      rethrow;
    }
  }

  Future<UserProfile> changePassword(
    String accessToken, {
    required String oldPassword,
    required String newPassword,
  }) async {
    try {
      final response = await dio.put(
        "$baseUrl/api/me/password",
        data: {"old_password": oldPassword, "new_password": newPassword},
        options: Options(
          headers: {"Authorization": "Bearer $accessToken"},
          extra: {"skipAuth": true},
        ),
      );
      if (response.statusCode == 200) {
        return UserProfile.fromJson(response.data as Map<String, dynamic>);
      }
      if (response.statusCode == 401) {
        throw telemetryException("Current password is incorrect");
      }
      if (response.statusCode == 400) {
        throw telemetryException(
          "Invalid new password: ${response.data?["detail"] ?? response.data}",
        );
      }
      throw telemetryException(
        "Password change failed with status ${response.statusCode}: ${response.data}",
      );
    } on DioException catch (e) {
      throw telemetryException("Password change request failed: ${e.message}");
    } on Object catch (error, stack) {
      TelemetryService.instance.capture(error, stack, code: "client_operation");
      rethrow;
    }
  }
}
