import "dart:async";
import "dart:convert";
import "dart:typed_data";

import "package:dio/dio.dart";
import "package:expenis_mobile/service/base_service.dart";
import "package:expenis_mobile/service/settings_service.dart";
import "package:flutter_test/flutter_test.dart";
import "package:shared_preferences/shared_preferences.dart";

class _ScriptedAdapter implements HttpClientAdapter {
  _ScriptedAdapter(this._handlers);

  final List<ResponseBody Function(RequestOptions options)> _handlers;
  int _index = 0;
  final List<RequestOptions> requests = [];

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    requests.add(options);
    if (_index >= _handlers.length) {
      throw StateError("Unexpected request ${options.method} ${options.uri}");
    }
    return _handlers[_index++](options);
  }

  @override
  void close({bool force = false}) {}
}

ResponseBody _json(int status, Map<String, dynamic> body) {
  return ResponseBody.fromString(
    jsonEncode(body),
    status,
    headers: {
      Headers.contentTypeHeader: ["application/json"],
    },
  );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() async {
    SettingsService.debugReset();
    SharedPreferences.setMockInitialValues({
      "access_token": "expired-access",
      "refresh_token": "valid-refresh",
    });
    await SettingsService.getInstance();
    BaseService.debugReset();
  });

  tearDown(BaseService.debugReset);

  test("retries original request after 401 once refresh succeeds", () async {
    final adapter = _ScriptedAdapter([
      (options) {
        expect(options.path.contains("/api/transactions"), isTrue);
        expect(options.headers["Authorization"], "Bearer expired-access");
        return _json(401, {
          "message": "Signature has expired",
          "error_type": "JWTDecodeError",
        });
      },
      (options) {
        expect(options.path.contains("/api/refresh"), isTrue);
        expect(options.headers["Authorization"], "Bearer valid-refresh");
        return _json(200, {
          "access_token": "new-access",
          "refresh_token": "new-refresh",
          "token_type": "bearer",
          "expires_in": 3600,
        });
      },
      (options) {
        expect(options.path.contains("/api/transactions"), isTrue);
        expect(options.headers["Authorization"], "Bearer new-access");
        return _json(200, {
          "transactions": <dynamic>[],
          "total_amount_rubles": 0,
        });
      },
    ]);

    final dio = createAuthedDio();
    dio.httpClientAdapter = adapter;
    final refreshDio = Dio(
      BaseOptions(
        validateStatus: (status) =>
            status != null && status >= 200 && status < 500,
      ),
    );
    refreshDio.httpClientAdapter = adapter;
    BaseService.debugSetDio(dio);
    BaseService.debugSetRefreshDio(refreshDio);

    final response = await dio.get("${resolveBaseUrl()}/api/transactions");

    expect(response.statusCode, 200);
    expect(adapter.requests.length, 3);
    final settings = await SettingsService.getInstance();
    expect(await settings.getAccessToken(), "new-access");
    expect(await settings.getRefreshToken(), "new-refresh");
  });

  test("does not refresh login 401s marked skipAuth", () async {
    final adapter = _ScriptedAdapter([
      (options) {
        expect(options.path.contains("/api/login"), isTrue);
        return _json(401, {"detail": "invalid credentials"});
      },
    ]);

    final dio = createAuthedDio();
    dio.httpClientAdapter = adapter;
    BaseService.debugSetDio(dio);

    final response = await dio.post(
      "${resolveBaseUrl()}/api/login",
      data: {"username": "u", "password": "bad"},
      options: Options(extra: {"skipAuth": true}),
    );

    expect(response.statusCode, 401);
    expect(adapter.requests.length, 1);
  });
}
