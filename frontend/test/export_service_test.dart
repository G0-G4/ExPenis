import "dart:async";
import "dart:convert";
import "dart:typed_data";

import "package:dio/dio.dart";
import "package:flutter_test/flutter_test.dart";
import "package:shared_preferences/shared_preferences.dart";

import "package:expenis_mobile/models/export.dart";
import "package:expenis_mobile/service/base_service.dart";
import "package:expenis_mobile/service/export_service.dart";
import "package:expenis_mobile/service/settings_service.dart";

class Adapter implements HttpClientAdapter {
  Adapter(this.handle);
  final ResponseBody Function(RequestOptions) handle;
  final requests = <RequestOptions>[];
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    requests.add(options);
    return handle(options);
  }

  @override
  void close({bool force = false}) {}
}

ResponseBody jsonBody(int code, Object body) => ResponseBody.fromString(
  jsonEncode(body),
  code,
  headers: {
    Headers.contentTypeHeader: ["application/json"],
  },
);

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() async {
    SettingsService.debugReset();
    SharedPreferences.setMockInitialValues({
      "access_token": "old",
      "refresh_token": "refresh",
    });
    await SettingsService.getInstance();
    BaseService.debugReset();
  });
  tearDown(BaseService.debugReset);

  void setup(Adapter adapter) {
    final dio = createAuthedDio()..httpClientAdapter = adapter;
    BaseService.debugSetDio(dio);
    BaseService.debugSetRefreshDio(Dio()..httpClientAdapter = adapter);
  }

  test(
    "downloads binary with repeated account params and inclusive dates",
    () async {
      setup(
        Adapter((options) {
          expect(options.responseType, ResponseType.bytes);
          expect(options.uri.queryParametersAll["account_ids"], ["1", "2"]);
          expect(options.queryParameters["date_from"], "2026-11-01");
          return ResponseBody.fromBytes(
            [1, 2, 3],
            200,
            headers: {
              "content-type": [ExportFormat.xlsx.mimeType],
              "content-disposition": ['attachment; filename="history.xlsx"'],
            },
          );
        }),
      );
      final file = await ExportService().export(
        ExportRequest(
          format: ExportFormat.xlsx,
          dateFrom: DateTime(2026, 11, 1),
          dateTo: DateTime(2026, 11, 21),
          accountIds: {1, 2},
        ),
      );
      expect(file.bytes, [1, 2, 3]);
      expect(file.name, "history.xlsx");
      expect(file.mimeType, ExportFormat.xlsx.mimeType);
    },
  );

  test(
    "binary download retries after refresh and preserves byte response",
    () async {
      var attempt = 0;
      final adapter = Adapter((options) {
        if (options.path.endsWith("/refresh")) {
          return jsonBody(200, {
            "access_token": "new",
            "refresh_token": "new-refresh",
          });
        }
        if (attempt++ == 0) return jsonBody(401, {"detail": "expired"});
        expect(options.headers["Authorization"], "Bearer new");
        expect(options.responseType, ResponseType.bytes);
        return ResponseBody.fromBytes(
          [239, 187, 191, 65],
          200,
          headers: {
            "content-type": ["text/csv; charset=utf-8"],
          },
        );
      });
      setup(adapter);
      final file = await ExportService().export(const ExportRequest());
      expect(file.bytes, [239, 187, 191, 65]);
      expect(file.name, "ExPenis-transactions.csv");
      expect(adapter.requests.length, 3);
    },
  );

  for (final status in [200, 404, 422]) {
    test("JSON $status is never a spreadsheet", () async {
      setup(
        Adapter((_) => jsonBody(status, {"detail": "Не удалось выгрузить"})),
      );
      await expectLater(
        ExportService().export(const ExportRequest()),
        throwsException,
      );
    });
  }

  test("fetches deleted account metadata", () async {
    setup(
      Adapter(
        (_) => jsonBody(200, {
          "accounts": [
            {
              "id": 1,
              "name": "Старый",
              "currency_code": "RUB",
              "is_deleted": true,
            },
          ],
        }),
      ),
    );
    final accounts = await ExportService().fetchAccounts();
    expect(accounts.single.displayName, "Старый (удалён)");
  });

  test("rejects invalid request before network", () async {
    setup(Adapter((_) => throw StateError("Must not request")));
    await expectLater(
      ExportService().export(const ExportRequest(accountIds: {})),
      throwsException,
    );
    expect(ExportRequest(dateFrom: DateTime(2026)).validationError, isNotNull);
    expect(
      ExportRequest(
        dateFrom: DateTime(2026, 2),
        dateTo: DateTime(2026, 1),
      ).validationError,
      isNotNull,
    );
  });
}
