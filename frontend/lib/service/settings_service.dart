import 'package:shared_preferences/shared_preferences.dart';

class SettingsService {
  static const String _apiKeyKey = 'api_key';

  static SettingsService? _instance;
  SharedPreferences? _prefs;

  SettingsService._();

  static Future<SettingsService> getInstance() async {
    _instance ??= SettingsService._();
    _instance!._prefs ??= await SharedPreferences.getInstance();
    return _instance!;
  }

  Future<String?> getApiKey() async {
    return _prefs?.getString(_apiKeyKey);
  }

  Future<bool> setApiKey(String apiKey) async {
    return await _prefs?.setString(_apiKeyKey, apiKey) ?? false;
  }

  Future<bool> clearApiKey() async {
    return await _prefs?.remove(_apiKeyKey) ?? false;
  }
}
