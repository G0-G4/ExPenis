import "dart:async";
import "dart:collection";
import "dart:convert";
import "dart:math";

import "package:dio/dio.dart";
import "package:flutter/foundation.dart";

const telemetryEnabled = bool.fromEnvironment(
  "EXPENIS_TELEMETRY_ENABLED",
  defaultValue: kReleaseMode,
);
const _sampling = String.fromEnvironment(
  "EXPENIS_TRACE_SAMPLE_RATE",
  defaultValue: "1",
);
final _random = Random.secure();
String telemetryId(int bytes) => List.generate(
  bytes,
  (_) => _random.nextInt(256).toRadixString(16).padLeft(2, "0"),
).join();
String _eventId() {
  final hex = telemetryId(16);
  return "${hex.substring(0, 8)}-${hex.substring(8, 12)}-${hex.substring(12, 16)}-${hex.substring(16, 20)}-${hex.substring(20)}";
}

int _nowNs() => DateTime.now().microsecondsSinceEpoch * 1000;

bool telemetrySamples(String traceId, double rate) {
  final product = rate.clamp(0, 1) * 18446744073709551616.0;
  var bound = BigInt.from(product);
  final fraction = product - bound.toDouble();
  if (fraction > .5 || (fraction == .5 && bound.isOdd)) bound += BigInt.one;
  return BigInt.parse(traceId.substring(16), radix: 16) < bound;
}

class TraceOperation {
  factory TraceOperation(String operation) {
    final traceId = telemetryId(16);
    return TraceOperation._(
      operation,
      traceId,
      telemetrySamples(traceId, double.tryParse(_sampling) ?? 1),
    );
  }
  TraceOperation._(this.operation, this.traceId, this.sampled)
    : spanId = telemetryId(8),
      startNs = _nowNs();
  final String operation;
  final String traceId;
  final String spanId;
  final int startNs;
  final bool sampled;
  final List<Map<String, String>> links = [];
  int lastStatus = 0;
  bool finished = false;
  bool reported = false;
}

class ReportedException implements Exception {
  ReportedException(this.message);
  final String message;
  @override
  String toString() => "Exception: $message";
}

/// UI text stays in the UI; it is never passed to the telemetry serializer.
Exception telemetryException(String message) => ReportedException(message);

List<Map<String, Object?>> telemetryFrames(StackTrace? stack) {
  final result = <Map<String, Object?>>[];
  final dart = RegExp(
    r"^\s*#\d+\s+(.+?) \((?:package:expenis_mobile/|file://[^\s)]+/frontend/lib/)([a-z0-9_/]+\.dart):(\d+)(?::\d+)?\)\s*$",
  );
  final js = RegExp(
    r"^\s*at\s+([A-Za-z_$][A-Za-z0-9_.$<>/-]*)\s+\([^()\s]*/main\.dart\.js(?:\?[^()\s]*)?:(\d+):\d+\)\s*$",
  );
  for (final line in (stack?.toString() ?? "").split("\n")) {
    final d = dart.firstMatch(line);
    final j = js.firstMatch(line);
    if (d == null && j == null) continue;
    var symbol = (d?[1] ?? j![1]!).replaceAll(
      RegExp(r"[^A-Za-z0-9_.$<>/-]"),
      "_",
    );
    if (symbol.length > 160) symbol = symbol.substring(0, 160);
    result.add({
      "file": d == null ? "main.dart.js" : "lib/${d[2]}",
      "function": symbol,
      "line": int.parse(d?[3] ?? j![2]!),
    });
    if (result.length == 30) break;
  }
  return result;
}

class TelemetryService {
  TelemetryService({
    this.enabled = false,
    this.platform = "web",
    this.version = "0.0.0",
    this.baseUrl = "",
    Dio? transport,
  }) : _transport =
           transport ??
           Dio(
             BaseOptions(
               connectTimeout: const Duration(seconds: 2),
               sendTimeout: const Duration(seconds: 2),
               receiveTimeout: const Duration(seconds: 2),
               followRedirects: false,
               validateStatus: (_) => true,
             ),
           );

  static TelemetryService instance = TelemetryService();
  bool enabled;
  final String platform;
  String version;
  final String baseUrl;
  final Dio _transport;
  final Queue<Map<String, Object?>> _queue = Queue();
  final Expando<bool> _reported = Expando<bool>();
  Timer? _timer;
  bool _sending = false;
  int _bytes = 0;
  int dropped = 0;
  int get queued => _queue.length;
  List<Map<String, Object?>> get pending => List.unmodifiable(_queue);

  void start() {
    if (enabled) {
      _timer ??= Timer.periodic(
        const Duration(seconds: 5),
        (_) => unawaited(flush()),
      );
    }
  }

  void dispose() {
    _timer?.cancel();
    _timer = null;
    _queue.clear();
    _bytes = 0;
    enabled = false;
    _transport.close(force: true);
  }

  void _add(Map<String, Object?> record) {
    if (!enabled) return;
    record = {
      "event_id": _eventId(),
      "timestamp": DateTime.now().toUtc().toIso8601String(),
      ...record,
    };
    final size = utf8.encode(jsonEncode(record)).length;
    if (size > 8192) {
      dropped++;
      return;
    }
    while (_queue.isNotEmpty &&
        (_queue.length >= 200 || _bytes + size > 1024 * 1024)) {
      _bytes -= utf8.encode(jsonEncode(_queue.removeFirst())).length;
      dropped++;
    }
    _queue.add(record);
    _bytes += size;
    if (_queue.length >= 50) unawaited(flush());
  }

  void capture(
    Object error,
    StackTrace? stack, {
    String code = "client_unhandled",
    TraceOperation? operation,
  }) {
    if (!enabled || error is ReportedException || operation?.reported == true) {
      return;
    }
    if (error is! String && error is! num && error is! bool) {
      if (_reported[error] == true) return;
      _reported[error] = true;
    }
    if (operation != null) operation.reported = true;
    final frames = telemetryFrames(stack);
    _add({
      "kind": "error",
      "code": code,
      "frames": frames,
      if (operation != null) "trace_id": operation.traceId,
      if (operation != null) "span_id": operation.spanId,
    });
  }

  void span(
    TraceOperation op,
    String spanId,
    int startNs,
    int status, {
    String? parent,
  }) {
    if (!op.sampled) return;
    final endNs = _nowNs();
    if (endNs < startNs || endNs - startNs > 15 * 60 * 1000000000) {
      if (enabled) dropped++;
      return;
    }
    _add({
      "kind": "span",
      "trace_id": op.traceId,
      "span_id": spanId,
      "parent_span_id": ?parent,
      if (parent == null && op.links.isNotEmpty)
        "links": op.links.take(4).toList(),
      "operation": op.operation,
      "start_ns": startNs,
      "end_ns": endNs,
      "status": status,
      "outcome": op.reported || status == 0 || status >= 500 ? "error" : "ok",
    });
  }

  void finish(TraceOperation op, int status) {
    if (op.finished) return;
    op.finished = true;
    span(op, op.spanId, op.startNs, status);
  }

  Future<void> flush() async {
    if (!enabled || _sending || _queue.isEmpty) return;
    _sending = true;
    final records = <Map<String, Object?>>[];
    var size = 256;
    while (_queue.isNotEmpty && records.length < 50) {
      final next = utf8.encode(jsonEncode(_queue.first)).length;
      if (size + next > 60000) break;
      records.add(_queue.removeFirst());
      size += next;
      _bytes -= next;
    }
    final payload = {
      "schema_version": 1,
      "platform": platform,
      "app_version": version,
      "records": records,
    };
    var delivered = false;
    try {
      for (var attempt = 0; attempt < 3 && enabled; attempt++) {
        Duration wait = Duration(milliseconds: 200 + _random.nextInt(100));
        Response<dynamic>? response;
        try {
          response = await _transport.post(
            "$baseUrl/api/telemetry",
            data: payload,
          );
        } on DioException catch (error) {
          // Delivery failure never calls capture or the auth client.
          response = error.response;
        }
        final status = response?.statusCode ?? 0;
        if (status == 202 || status == 204) {
          delivered = true;
          break;
        }
        if (response != null &&
            status != 429 &&
            status != 503 &&
            status < 500) {
          break;
        }
        final retry = int.tryParse(
          response?.headers.value("retry-after") ?? "",
        );
        if (retry != null) wait = Duration(seconds: retry.clamp(0, 5));
        if (attempt < 2) await Future<void>.delayed(wait);
      }
    } finally {
      if (!delivered) dropped += records.length;
      _sending = false;
    }
  }
}

class TelemetryInterceptor extends Interceptor {
  TelemetryInterceptor({
    this.operation = "api",
    this.firstPartyOrigin = "https://expenis.g0g4.ru",
  });
  final String operation;
  final String firstPartyOrigin;

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    final telemetry = TelemetryService.instance;
    if (!telemetry.enabled || options.path.endsWith("/api/telemetry")) {
      handler.next(options);
      return;
    }
    final op =
        options.extra["telemetryOperation"] as TraceOperation? ??
        TraceOperation(operation);
    options.extra["telemetryOperation"] = op;
    options.extra["telemetryAttempt"] = telemetryId(8);
    options.extra["telemetryStart"] = _nowNs();
    final uri = options.uri;
    if (uri.origin == firstPartyOrigin &&
        uri.path.startsWith("/api/") &&
        !uri.path.startsWith("/api/health/")) {
      options.headers["traceparent"] =
          "00-${op.traceId}-${options.extra["telemetryAttempt"]}-${op.sampled ? "01" : "00"}";
      // Do not let a redirect carry first-party headers into another origin.
      options.followRedirects = false;
    }
    handler.next(options);
  }

  void _end(
    RequestOptions request,
    int status, {
    Object? error,
    StackTrace? stack,
  }) {
    final op = request.extra["telemetryOperation"] as TraceOperation?;
    if (op == null) return;
    final telemetry = TelemetryService.instance;
    op.lastStatus = status;
    telemetry.span(
      op,
      request.extra["telemetryAttempt"] as String,
      request.extra["telemetryStart"] as int,
      status,
      parent: op.spanId,
    );
    final pendingRefresh =
        status == 401 &&
        request.extra["skipAuth"] != true &&
        request.extra["retried"] != true &&
        operation == "api";
    if (!pendingRefresh && request.extra["telemetryRefreshChild"] != true) {
      telemetry.finish(op, status);
    }
    if (status == 0 || status >= 500) {
      telemetry.capture(
        error ?? StateError("http_failure"),
        stack,
        code: status == 0 ? "client_network" : "client_http",
        operation: op,
      );
    }
  }

  @override
  void onResponse(Response response, ResponseInterceptorHandler handler) {
    _end(response.requestOptions, response.statusCode ?? 0);
    handler.next(response);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    _end(
      err.requestOptions,
      err.response?.statusCode ?? 0,
      error: err,
      stack: err.stackTrace,
    );
    handler.next(err);
  }
}
