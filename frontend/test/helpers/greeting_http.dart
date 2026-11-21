import "dart:async";
import "dart:convert";
import "dart:typed_data";

import "package:dio/dio.dart";

class GreetingHttp implements HttpClientAdapter {
  final requests = <RequestOptions>[];
  Map<String, dynamic>? greeting;
  int readStatus = 200;
  int dismissStatus = 204;
  Completer<ResponseBody>? pendingRead;
  Completer<ResponseBody>? pendingDismiss;

  int get reads =>
      requests.where((r) => r.path.endsWith("/me/greeting")).length;

  static ResponseBody json(Object? data, [int status = 200]) =>
      ResponseBody.fromString(
        jsonEncode(data),
        status,
        headers: {
          Headers.contentTypeHeader: ["application/json"],
        },
      );

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    requests.add(options);
    if (options.path.endsWith("/me/greeting")) {
      final pending = pendingRead;
      pendingRead = null;
      return pending?.future ?? json({"greeting": greeting}, readStatus);
    }
    if (options.path.endsWith("/dismiss")) {
      final pending = pendingDismiss;
      pendingDismiss = null;
      if (pending != null) return pending.future;
      if (dismissStatus == 204) greeting = null;
      return json(null, dismissStatus);
    }
    if (options.path.endsWith("/transactions")) {
      return json({"transactions": [], "total_amount_rubles": 0});
    }
    if (options.path.endsWith("/accounts")) {
      return json({"accounts": {}, "total_amount_rubles": 0});
    }
    if (options.path.endsWith("/categories")) {
      return json({"income": [], "expense": []});
    }
    throw StateError("Unexpected request: ${options.path}");
  }

  @override
  void close({bool force = false}) {}
}

Map<String, dynamic> greetingJson(
  String text, {
  String id = "assignment-A",
  DateTime? expiry,
}) => {"id": id, "text": text, "expires_at": expiry?.toUtc().toIso8601String()};
