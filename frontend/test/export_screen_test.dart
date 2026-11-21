import "dart:async";
import "dart:convert";

import "package:flutter/material.dart";
import "package:flutter/foundation.dart";
import "package:flutter/services.dart";
import "package:dio/dio.dart";
import "package:shared_preferences/shared_preferences.dart";
import "package:flutter_test/flutter_test.dart";

import "package:expenis_mobile/models/export.dart";
import "package:expenis_mobile/screens/export_screen.dart";
import "package:expenis_mobile/screens/settings_screen.dart";
import "package:expenis_mobile/service/base_service.dart";
import "package:expenis_mobile/service/settings_service.dart";

class FakeExportAdapter implements HttpClientAdapter {
  List<ExportAccount> accounts = const [
    ExportAccount(
      id: 1,
      name: "Основной",
      currencyCode: "RUB",
      isDeleted: false,
    ),
    ExportAccount(id: 2, name: "Старый", currencyCode: "EUR", isDeleted: true),
  ];
  bool failAccounts = false;
  bool failExport = false;
  Completer<ExportFile>? pending;
  final requests = <ExportRequest>[];
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? stream,
    Future<void>? cancel,
  ) async {
    if (options.path.endsWith("/me")) {
      return ResponseBody.fromString(
        jsonEncode({"id": 1, "username": "test", "telegram_id": null}),
        200,
        headers: {
          "content-type": ["application/json"],
        },
      );
    }
    if (options.path.endsWith("/accounts")) {
      if (failAccounts) throw Exception("accounts unavailable");
      return ResponseBody.fromString(
        jsonEncode({
          "accounts": [
            for (final account in accounts)
              {
                "id": account.id,
                "name": account.name,
                "currency_code": account.currencyCode,
                "is_deleted": account.isDeleted,
              },
          ],
        }),
        200,
        headers: {
          "content-type": ["application/json"],
        },
      );
    }
    final query = options.queryParameters;
    final format = query["format"] == "xlsx"
        ? ExportFormat.xlsx
        : ExportFormat.csv;
    requests.add(
      ExportRequest(
        format: format,
        dateFrom: DateTime.tryParse(query["date_from"] as String? ?? ""),
        dateTo: DateTime.tryParse(query["date_to"] as String? ?? ""),
        accountIds: (query["account_ids"] as List?)?.cast<int>().toSet(),
      ),
    );
    if (failExport) {
      return ResponseBody.fromString(
        jsonEncode({"detail": "Не удалось экспортировать операции"}),
        422,
        headers: {
          "content-type": ["application/json"],
        },
      );
    }
    final result = pending == null ? file : await pending!.future;
    return ResponseBody.fromBytes(
      result.bytes,
      200,
      headers: {
        "content-type": [format.mimeType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
  static final file = ExportFile(
    bytes: Uint8List.fromList([1, 2]),
    name: "history.csv",
    mimeType: "text/csv",
  );
}

void main() {
  Future<void> open(WidgetTester tester, FakeExportAdapter service) async {
    BaseService.debugReset();
    SettingsService.debugReset();
    SharedPreferences.setMockInitialValues({});
    await SettingsService.getInstance();
    BaseService.debugSetDio(createAuthedDio()..httpClientAdapter = service);
    tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
      const MethodChannel("plugins.flutter.io/file_selector"),
      (_) async => null,
    );
    addTearDown(() {
      BaseService.debugReset();
      tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
        const MethodChannel("plugins.flutter.io/file_selector"),
        null,
      );
    });
    tester.view.physicalSize = const Size(1000, 1800);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(const MaterialApp(home: ExportScreen()));
    await tester.pumpAndSettle();
  }

  Finder submit() => find.byKey(const Key("export-submit"));
  Future<void> press(WidgetTester tester) async {
    await tester.ensureVisible(submit());
    await tester.tap(submit());
    await tester.pumpAndSettle();
  }

  testWidgets(
    "settings opens export screen",
    (tester) async {
      final service = FakeExportAdapter();
      await open(tester, service);
      await tester.pumpWidget(const MaterialApp(home: SettingsScreen()));
      await tester.pumpAndSettle();
      await tester.tap(find.text("Экспорт операций"));
      await tester.pumpAndSettle();
      expect(find.byType(ExportScreen), findsOneWidget);
      expect(find.text("За всё время"), findsOneWidget);
    },
    variant: TargetPlatformVariant.only(TargetPlatform.linux),
  );

  testWidgets(
    "defaults export all history and all accounts as CSV",
    (tester) async {
      final service = FakeExportAdapter();
      await open(tester, service);
      expect(find.text("Экспорт операций"), findsOneWidget);
      expect(find.text("За всё время"), findsOneWidget);
      expect(find.text("Все счета"), findsOneWidget);
      expect(find.text("Категории"), findsNothing);
      expect(find.text("Теги"), findsNothing);
      await press(tester);
      expect(service.requests.single.format, ExportFormat.csv);
      expect(service.requests.single.accountIds, isNull);
      expect(service.requests.single.dateFrom, isNull);
      expect(find.text("Файл сохранён"), findsNothing);
    },
    variant: TargetPlatformVariant.only(TargetPlatform.linux),
  );

  testWidgets(
    "explicit deleted account and XLSX are sent",
    (tester) async {
      final service = FakeExportAdapter();
      await open(tester, service);
      await tester.tap(find.text("Все счета"));
      await tester.pumpAndSettle();
      expect(find.text("Старый (удалён)"), findsOneWidget);
      expect(tester.widget<FilledButton>(submit()).onPressed, isNull);
      await tester.tap(find.text("Старый (удалён)"));
      await tester.tap(find.text("XLSX"));
      await tester.pumpAndSettle();
      await press(tester);
      expect(service.requests.single.accountIds, {2});
      expect(service.requests.single.format, ExportFormat.xlsx);
    },
    variant: TargetPlatformVariant.only(TargetPlatform.linux),
  );

  testWidgets(
    "period selection is required and propagated",
    (tester) async {
      final service = FakeExportAdapter();
      await open(tester, service);
      await tester.tap(find.text("За всё время"));
      await tester.pumpAndSettle();
      expect(tester.widget<FilledButton>(submit()).onPressed, isNull);
      await tester.tap(find.byKey(const Key("export-period")));
      await tester.pumpAndSettle();
      await tester.tap(find.text("Выбрать"));
      await tester.pumpAndSettle();
      await press(tester);
      expect(service.requests.single.dateFrom, isNotNull);
      expect(service.requests.single.dateTo, isNotNull);
    },
    variant: TargetPlatformVariant.only(TargetPlatform.linux),
  );

  testWidgets(
    "failed export retains filters and can retry",
    (tester) async {
      final service = FakeExportAdapter()..failExport = true;
      await open(tester, service);
      await tester.tap(find.text("XLSX"));
      await tester.pumpAndSettle();
      await press(tester);
      expect(find.text("Не удалось экспортировать операции"), findsOneWidget);
      service.failExport = false;
      await press(tester);
      expect(service.requests.map((r) => r.format), [
        ExportFormat.xlsx,
        ExportFormat.xlsx,
      ]);
      expect(find.text("Не удалось экспортировать операции"), findsNothing);
    },
    variant: TargetPlatformVariant.only(TargetPlatform.linux),
  );

  testWidgets(
    "empty account catalog can export header-only file",
    (tester) async {
      final service = FakeExportAdapter()..accounts = [];
      await open(tester, service);
      await press(tester);
      expect(service.requests.length, 1);
    },
    variant: TargetPlatformVariant.only(TargetPlatform.linux),
  );

  testWidgets(
    "catalog load failure has retry",
    (tester) async {
      final service = FakeExportAdapter()..failAccounts = true;
      await open(tester, service);
      expect(tester.widget<FilledButton>(submit()).onPressed, isNull);
      service.failAccounts = false;
      await tester.tap(find.text("Повторить загрузку"));
      await tester.pumpAndSettle();
      expect(tester.widget<FilledButton>(submit()).onPressed, isNotNull);
    },
    variant: TargetPlatformVariant.only(TargetPlatform.linux),
  );

  testWidgets(
    "pending request disables repeat and closing screen is safe",
    (tester) async {
      final service = FakeExportAdapter()..pending = Completer<ExportFile>();
      await open(tester, service);
      await tester.tap(submit());
      for (var i = 0; i < 10 && service.requests.isEmpty; i++) {
        await tester.pump(const Duration(milliseconds: 10));
      }
      expect(service.requests.length, 1);
      expect(tester.widget<FilledButton>(submit()).onPressed, isNull);
      await tester.pumpWidget(const MaterialApp(home: SizedBox()));
      service.pending!.complete(FakeExportAdapter.file);
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
    },
    variant: TargetPlatformVariant.only(TargetPlatform.linux),
  );
}
