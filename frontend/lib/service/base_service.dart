import "package:dio/dio.dart";
import "package:flutter/foundation.dart";
import "package:expenis_mobile/service/auth_service.dart";
import "package:expenis_mobile/service/navigator_service.dart";
import "package:expenis_mobile/service/platform_config.dart"
    if (dart.library.io) "package:expenis_mobile/service/platform_config_io.dart";
import "package:expenis_mobile/service/settings_service.dart";

abstract class BaseService {
  late final Dio _dio;

  BaseService() {
    _dio = Dio(
      BaseOptions(
        validateStatus: (status) {
          return status! >= 200 && status < 500;
        },
      ),
    );

    _dio.interceptors.add(
      QueuedInterceptorsWrapper(
        onRequest: (options, handler) async {
          if (options.extra["skipAuth"] == true) {
            handler.next(options);
            return;
          }
          final settingsService = await SettingsService.getInstance();
          final accessToken = await settingsService.getAccessToken();
          if (accessToken != null && accessToken.isNotEmpty) {
            options.headers["Authorization"] = "Bearer $accessToken";
          }
          handler.next(options);
        },
        onError: (error, handler) async {
          final request = error.requestOptions;
          if (request.extra["skipAuth"] == true ||
              request.extra["retried"] == true ||
              error.response?.statusCode != 401) {
            handler.next(error);
            return;
          }
          final refreshed = await _tryRefresh();
          if (!refreshed) {
            await _forceLogout();
            handler.next(error);
            return;
          }
          try {
            request.extra["retried"] = true;
            final settingsService = await SettingsService.getInstance();
            final accessToken = await settingsService.getAccessToken();
            if (accessToken != null && accessToken.isNotEmpty) {
              request.headers["Authorization"] = "Bearer $accessToken";
            }
            final response = await _dio.fetch(request);
            handler.resolve(response);
          } on DioException catch (e) {
            handler.next(e);
          }
        },
      ),
    );
  }

  Future<bool> _tryRefresh() async {
    try {
      final settingsService = await SettingsService.getInstance();
      final refreshToken = await settingsService.getRefreshToken();
      if (refreshToken == null || refreshToken.isEmpty) {
        return false;
      }
      final authService = AuthService();
      final session = await authService.refresh(refreshToken);
      await settingsService.setAccessToken(session.accessToken);
      await settingsService.setRefreshToken(session.refreshToken);
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<void> _forceLogout() async {
    final settingsService = await SettingsService.getInstance();
    await settingsService.clearAuth();
    final navigator = appNavigatorKey.currentState;
    if (navigator != null) {
      navigator.pushNamedAndRemoveUntil("/login", (_) => false);
    }
  }

  Dio get dio => _dio;

  String get baseUrl {
    if (kReleaseMode) {
      return "https://expenis.g0g4.ru";
    }
    return debugBaseUrl;
  }
}
