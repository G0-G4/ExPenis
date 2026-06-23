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
      );
      if (response.statusCode == 200 || response.statusCode == 201) {
        return AuthSession.fromJson(response.data as Map<String, dynamic>);
      }
      if (response.statusCode == 401) {
        throw Exception("Invalid username or password");
      }
      throw Exception(
        "Login failed with status ${response.statusCode}: ${response.data}",
      );
    } on DioException catch (e) {
      throw Exception("Login request failed: ${e.message}");
    }
  }

  Future<AuthSession> register(String username, String password) async {
    try {
      final response = await dio.post(
        "$baseUrl/api/register",
        data: {"username": username, "password": password},
      );
      if (response.statusCode == 200 || response.statusCode == 201) {
        return AuthSession.fromJson(response.data as Map<String, dynamic>);
      }
      if (response.statusCode == 409) {
        throw Exception("Username is already taken");
      }
      if (response.statusCode == 422) {
        throw Exception("Invalid input: ${response.data}");
      }
      throw Exception(
        "Registration failed with status ${response.statusCode}: ${response.data}",
      );
    } on DioException catch (e) {
      throw Exception("Registration request failed: ${e.message}");
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
      throw Exception(
        "Token refresh failed with status ${response.statusCode}",
      );
    } on DioException catch (e) {
      throw Exception("Token refresh request failed: ${e.message}");
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
      throw Exception("Logout request failed: ${e.message}");
    }
  }

  Future<UserProfile> me(String accessToken) async {
    try {
      final response = await dio.get(
        "$baseUrl/api/me",
        options: Options(
          headers: {"Authorization": "Bearer $accessToken"},
          extra: {"skipAuth": true},
        ),
      );
      if (response.statusCode == 200) {
        return UserProfile.fromJson(response.data as Map<String, dynamic>);
      }
      throw Exception(
        "Failed to load profile with status ${response.statusCode}",
      );
    } on DioException catch (e) {
      throw Exception("Failed to load profile: ${e.message}");
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
        throw Exception("Current password is incorrect");
      }
      if (response.statusCode == 400) {
        throw Exception(
          "Invalid new password: ${response.data?["detail"] ?? response.data}",
        );
      }
      throw Exception(
        "Password change failed with status ${response.statusCode}: ${response.data}",
      );
    } on DioException catch (e) {
      throw Exception("Password change request failed: ${e.message}");
    }
  }
}
