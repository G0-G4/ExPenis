import "dart:async";
import "dart:convert";
import "dart:typed_data";
import "package:dio/dio.dart";
import "package:flutter_test/flutter_test.dart";
import "package:expenis_mobile/service/base_service.dart";
import "package:expenis_mobile/service/settings_service.dart";
import "package:expenis_mobile/service/telemetry_service.dart";
import "package:shared_preferences/shared_preferences.dart";

class Adapter implements HttpClientAdapter {
  Adapter(this.respond);
  final ResponseBody Function(RequestOptions) respond;
  final List<Map<String, Object?>> seen = [];
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    seen.add({
      "headers": Map.of(options.headers),
      "extra": Map.of(options.extra),
    });
    return respond(options);
  }

  @override
  void close({bool force = false}) {}
}

ResponseBody reply(int status, [Map<String, Object?> data = const {}]) =>
    ResponseBody.fromString(
      jsonEncode(data),
      status,
      headers: {
        Headers.contentTypeHeader: ["application/json"],
      },
    );

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  tearDown(() {
    TelemetryService.instance.dispose();
    BaseService.debugReset();
  });
  test("bounded queue, safe errors, occurrence deduplication", () {
    final service = TelemetryService(enabled: true);
    final error = StateError("private-password@example.com amount=987654");
    service.capture(error, StackTrace.current);
    service.capture(error, StackTrace.current);
    expect(service.queued, 1);
    expect(jsonEncode(service.pending), isNot(contains("private-password")));
    for (var i = 0; i < 300; i++) {
      service.capture(StateError("secret"), null);
    }
    expect(service.queued, lessThanOrEqualTo(200));
    expect(service.dropped, greaterThan(0));
    service.dispose();
  });
  test("disabled collection stays empty", () {
    final service = TelemetryService();
    service.capture(StateError("secret"), StackTrace.current);
    expect(service.queued, 0);
  });
  test("refresh and retry share trace with separate attempts", () async {
    SettingsService.debugReset();
    SharedPreferences.setMockInitialValues({
      "access_token": "old",
      "refresh_token": "refresh",
    });
    await SettingsService.getInstance();
    TelemetryService.instance = TelemetryService(
      enabled: true,
      baseUrl: resolveBaseUrl(),
    );
    var calls = 0;
    final adapter = Adapter((options) {
      calls++;
      if (calls == 1) return reply(401);
      if (calls == 2) {
        return reply(200, {
          "access_token": "new",
          "refresh_token": "new-refresh",
        });
      }
      return reply(200);
    });
    final dio = createAuthedDio()..httpClientAdapter = adapter;
    final refresh = Dio(BaseOptions(validateStatus: (_) => true))
      ..httpClientAdapter = adapter;
    refresh.interceptors.add(
      TelemetryInterceptor(firstPartyOrigin: resolveBaseUrl()),
    );
    BaseService.debugSetRefreshDio(refresh);
    expect(
      (await dio.get("${resolveBaseUrl()}/api/transactions")).statusCode,
      200,
    );
    expect(calls, 3);
    final headers = adapter.seen
        .map((r) => (r["headers"] as Map)["traceparent"] as String)
        .toList();
    expect(headers.map((h) => h.split("-")[1]).toSet().length, 1);
    expect(headers.map((h) => h.split("-")[2]).toSet().length, 3);
    expect(
      TelemetryService.instance.pending
          .where((r) => r["kind"] == "span")
          .length,
      4,
    );
    expect(
      TelemetryService.instance.pending.where((r) => r["kind"] == "error"),
      isEmpty,
    );
  });
  test("third-party expected 401 sends no trace headers or error", () async {
    TelemetryService.instance = TelemetryService(enabled: true);
    final adapter = Adapter((_) => reply(401));
    final dio = Dio(BaseOptions(validateStatus: (_) => true))
      ..httpClientAdapter = adapter;
    dio.interceptors.add(TelemetryInterceptor());
    await dio.post(
      "https://example.org/api/login",
      options: Options(extra: {"skipAuth": true}),
    );
    expect(
      (adapter.seen.single["headers"] as Map).containsKey("traceparent"),
      false,
    );
    expect(
      TelemetryService.instance.pending.where((r) => r["kind"] == "error"),
      isEmpty,
    );
  });
  test("delivery uses no auth or tracing headers", () async {
    final adapter = Adapter((options) {
      expect(options.headers.containsKey("Authorization"), false);
      expect(options.headers.containsKey("traceparent"), false);
      return reply(202);
    });
    final transport = Dio()..httpClientAdapter = adapter;
    final service = TelemetryService(
      enabled: true,
      baseUrl: "https://example.org",
      transport: transport,
    );
    service.capture(StateError("secret"), null);
    await service.flush();
    expect(service.queued, 0);
    expect(service.dropped, 0);
    service.dispose();
  });
  test("invalid clock spans cannot poison a valid error batch", () async {
    final adapter = Adapter((options) {
      final records = (options.data as Map)["records"] as List;
      expect(records.length, 1);
      expect((records.single as Map)["kind"], "error");
      return reply(202);
    });
    final service = TelemetryService(
      enabled: true,
      baseUrl: "https://example.org",
      transport: Dio()..httpClientAdapter = adapter,
    );
    final op = TraceOperation("api");
    service.capture(StateError("private"), null, operation: op);
    for (final start in [
      DateTime.now().add(const Duration(hours: 1)).microsecondsSinceEpoch *
          1000,
      DateTime.now()
              .subtract(const Duration(minutes: 16))
              .microsecondsSinceEpoch *
          1000,
      0,
    ]) {
      service.span(op, telemetryId(8), start, 200);
    }
    expect(service.queued, 1);
    expect(service.dropped, 3);
    await service.flush();
    expect(adapter.seen.length, 1);
    expect(service.queued, 0);
    service.dispose();
  });
  test(
    "schema rejection stays terminal without splitting or retries",
    () async {
      final adapter = Adapter((_) => reply(422));
      final service = TelemetryService(
        enabled: true,
        baseUrl: "https://example.org",
        transport: Dio()..httpClientAdapter = adapter,
      );
      service.capture(StateError("private"), null);
      await service.flush();
      expect(adapter.seen.length, 1);
      expect(service.dropped, 1);
      expect(service.queued, 0);
      service.dispose();
    },
  );
  test("sampling uses the same low-64-bit threshold as OTel", () {
    expect(telemetrySamples("00000000000000000000000000000001", 0), false);
    expect(telemetrySamples("ffffffffffffffffffffffffffffffff", 1), true);
    expect(telemetrySamples("00000000000000007fffffffffffffff", .5), true);
    expect(telemetrySamples("00000000000000008000000000000000", .5), false);
  });

  test("failed refresh preserves auth behavior and completes trace", () async {
    SettingsService.debugReset();
    SharedPreferences.setMockInitialValues({
      "access_token": "old",
      "refresh_token": "expired",
    });
    await SettingsService.getInstance();
    TelemetryService.instance = TelemetryService(enabled: true);
    final adapter = Adapter((_) => reply(401));
    final dio = createAuthedDio()..httpClientAdapter = adapter;
    final refresh = Dio(BaseOptions(validateStatus: (_) => true))
      ..httpClientAdapter = adapter;
    refresh.interceptors.add(
      TelemetryInterceptor(firstPartyOrigin: resolveBaseUrl()),
    );
    BaseService.debugSetRefreshDio(refresh);
    expect(
      (await dio.get("${resolveBaseUrl()}/api/transactions")).statusCode,
      401,
    );
    expect(adapter.seen.length, 2);
    expect(
      await (await SettingsService.getInstance()).getAccessToken(),
      isNull,
    );
    expect(
      TelemetryService.instance.pending.where((r) => r["kind"] == "error"),
      isEmpty,
    );
  });
  test("stack locations omit local paths, URL queries and error text", () {
    final frames = telemetryFrames(
      StackTrace.fromString(
        "Error: private-email@example.com\n"
        "#0 load (package:expenis_mobile/service/auth_service.dart:13:4)\n"
        "#1 main.<anonymous closure> (file:///home/private/frontend/lib/main.dart:40:1)\n"
        "    at Object.handle (https://example.org/main.dart.js?token=private-canary:200:30)",
      ),
    );
    expect(frames.length, 3);
    expect(frames.last["file"], "main.dart.js");
    expect(jsonEncode(frames), isNot(contains("private")));
    expect(jsonEncode(frames), isNot(contains("example.org")));
  });
  test(
    "coalesced refresh preserves a link without duplicate HTTP calls",
    () async {
      SettingsService.debugReset();
      SharedPreferences.setMockInitialValues({"refresh_token": "refresh"});
      await SettingsService.getInstance();
      TelemetryService.instance = TelemetryService(enabled: true);
      var calls = 0;
      final adapter = Adapter((_) {
        calls++;
        return reply(200, {
          "access_token": "new",
          "refresh_token": "new-refresh",
        });
      });
      final client = Dio(BaseOptions(validateStatus: (_) => true))
        ..httpClientAdapter = adapter;
      client.interceptors.add(
        TelemetryInterceptor(firstPartyOrigin: resolveBaseUrl()),
      );
      BaseService.debugSetRefreshDio(client);
      final owner = TraceOperation("api");
      final waiter = TraceOperation("api");
      await Future.wait([
        refreshStoredTokens(operation: owner),
        refreshStoredTokens(operation: waiter),
      ]);
      expect(calls, 1);
      expect(waiter.links.single, {
        "trace_id": owner.traceId,
        "span_id": owner.spanId,
      });
    },
  );
}
