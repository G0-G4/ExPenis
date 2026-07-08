import 'package:shared_preferences/shared_preferences.dart';

class SettingsService {
  static const String _accessTokenKey = "access_token";
  static const String _refreshTokenKey = "refresh_token";
  static const String _usernameKey = "username";
  static const String _excludedAccountIdsKeyPrefix = "excluded_account_ids_";

  static SettingsService? _instance;
  SharedPreferences? _prefs;

  SettingsService._();

  static Future<SettingsService> getInstance() async {
    _instance ??= SettingsService._();
    _instance!._prefs ??= await SharedPreferences.getInstance();
    return _instance!;
  }

  Future<String?> getAccessToken() async {
    return _prefs?.getString(_accessTokenKey);
  }

  Future<bool> setAccessToken(String accessToken) async {
    return await _prefs?.setString(_accessTokenKey, accessToken) ?? false;
  }

  Future<String?> getRefreshToken() async {
    return _prefs?.getString(_refreshTokenKey);
  }

  Future<bool> setRefreshToken(String refreshToken) async {
    return await _prefs?.setString(_refreshTokenKey, refreshToken) ?? false;
  }

  Future<String?> getUsername() async {
    return _prefs?.getString(_usernameKey);
  }

  Future<bool> setUsername(String? username) async {
    if (username == null || username.isEmpty) {
      return await _prefs?.remove(_usernameKey) ?? false;
    }
    return await _prefs?.setString(_usernameKey, username) ?? false;
  }

  Future<bool> hasAccessToken() async {
    final token = await getAccessToken();
    return token != null && token.isNotEmpty;
  }

  Future<void> clearAuth() async {
    await _prefs?.remove(_accessTokenKey);
    await _prefs?.remove(_refreshTokenKey);
    await _prefs?.remove(_usernameKey);
  }

  Future<Set<String>> getExcludedAccountIds(int userId) async {
    final list = _prefs?.getStringList("$_excludedAccountIdsKeyPrefix$userId");
    return list?.toSet() ?? <String>{};
  }

  Future<bool> setExcludedAccountIds(int userId, Set<String> ids) async {
    return await _prefs
            ?.setStringList("$_excludedAccountIdsKeyPrefix$userId", ids.toList()) ??
        false;
  }
}
