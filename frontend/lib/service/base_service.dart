import "package:dio/dio.dart";
import "package:flutter/foundation.dart";
import "package:expenis_mobile/service/navigator_service.dart";
import "package:expenis_mobile/service/platform_config.dart"
    if (dart.library.io) "package:expenis_mobile/service/platform_config_io.dart";
import "package:expenis_mobile/service/settings_service.dart";

enum TokenRefreshResult { success, unauthorized, failed }

String resolveBaseUrl() {
  if (kReleaseMode) {
    return "https://expenis.g0g4.ru";
  }
  return debugBaseUrl;
}

Future<TokenRefreshResult>? _refreshInFlight;
Dio? _refreshDio;

Dio _plainDio({HttpClientAdapter? adapter}) {
  final client = Dio(
    BaseOptions(
      validateStatus: (status) =>
          status != null && status >= 200 && status < 500,
    ),
  );
  if (adapter != null) {
    client.httpClientAdapter = adapter;
  }
  return client;
}

/// Refresh using a Dio without the auth interceptor to avoid a queued-interceptor deadlock.
Future<TokenRefreshResult> refreshStoredTokens() {
  return _refreshInFlight ??= _refreshStoredTokens().whenComplete(() {
    _refreshInFlight = null;
  });
}

Future<TokenRefreshResult> _refreshStoredTokens() async {
  try {
    final settingsService = await SettingsService.getInstance();
    final refreshToken = await settingsService.getRefreshToken();
    if (refreshToken == null || refreshToken.isEmpty) {
      return TokenRefreshResult.unauthorized;
    }
    final response = await (_refreshDio ?? _plainDio()).post(
      "${resolveBaseUrl()}/api/refresh",
      options: Options(headers: {"Authorization": "Bearer $refreshToken"}),
    );
    if (response.statusCode != 200 && response.statusCode != 201) {
      return response.statusCode == 401
          ? TokenRefreshResult.unauthorized
          : TokenRefreshResult.failed;
    }
    final data = response.data;
    if (data is! Map) {
      return TokenRefreshResult.failed;
    }
    final accessToken = data["access_token"];
    final newRefreshToken = data["refresh_token"];
    if (accessToken is! String ||
        accessToken.isEmpty ||
        newRefreshToken is! String ||
        newRefreshToken.isEmpty) {
      return TokenRefreshResult.failed;
    }
    await settingsService.setAccessToken(accessToken);
    await settingsService.setRefreshToken(newRefreshToken);
    return TokenRefreshResult.success;
  } on DioException catch (error) {
    if (error.response?.statusCode == 401) {
      return TokenRefreshResult.unauthorized;
    }
    return TokenRefreshResult.failed;
  } catch (_) {
    return TokenRefreshResult.failed;
  }
}

Future<void> forceLogout() async {
  final settingsService = await SettingsService.getInstance();
  await settingsService.clearAuth();
  final navigator = appNavigatorKey.currentState;
  if (navigator != null) {
    navigator.pushNamedAndRemoveUntil("/login", (_) => false);
  }
}

bool _shouldAttemptRefresh(Response response) {
  final request = response.requestOptions;
  if (response.statusCode != 401) {
    return false;
  }
  if (request.extra["skipAuth"] == true || request.extra["retried"] == true) {
    return false;
  }
  return true;
}

Dio createAuthedDio() {
  final dio = Dio(
    BaseOptions(
      validateStatus: (status) {
        return status != null && status >= 200 && status < 500;
      },
    ),
  );

  dio.interceptors.add(
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
      onResponse: (response, handler) async {
        if (!_shouldAttemptRefresh(response)) {
          handler.next(response);
          return;
        }
        final result = await refreshStoredTokens();
        if (result != TokenRefreshResult.success) {
          if (result == TokenRefreshResult.unauthorized) {
            await forceLogout();
          }
          handler.next(response);
          return;
        }
        try {
          final request = response.requestOptions;
          request.extra["retried"] = true;
          final settingsService = await SettingsService.getInstance();
          final accessToken = await settingsService.getAccessToken();
          if (accessToken != null && accessToken.isNotEmpty) {
            request.headers["Authorization"] = "Bearer $accessToken";
          }
          // Retry on a Dio without interceptors — fetching through this
          // QueuedInterceptorsWrapper would deadlock.
          final retry = await _plainDio(
            adapter: dio.httpClientAdapter,
          ).fetch(request);
          handler.resolve(retry);
        } on DioException catch (error) {
          handler.next(error.response ?? response);
        }
      },
    ),
  );
  return dio;
}

abstract class BaseService {
  static Dio? _sharedDio;

  @visibleForTesting
  static void debugReset() {
    _sharedDio = null;
    _refreshInFlight = null;
    _refreshDio = null;
  }

  @visibleForTesting
  static void debugSetDio(Dio dio) {
    _sharedDio = dio;
  }

  @visibleForTesting
  static void debugSetRefreshDio(Dio dio) {
    _refreshDio = dio;
  }

  Dio get dio => _sharedDio ??= createAuthedDio();

  String get baseUrl => resolveBaseUrl();
}
