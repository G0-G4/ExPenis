import "dart:io";
import "dart:ui" as ui;

import "package:dio/dio.dart";
import "package:flutter/material.dart";
import "package:flutter/rendering.dart";
import "package:flutter/services.dart";
import "package:flutter_test/flutter_test.dart";
import "package:fl_chart/fl_chart.dart";

import "package:expenis_mobile/models/category.dart";
import "package:expenis_mobile/screens/edit_category_screen.dart";
import "package:expenis_mobile/screens/transaction_stats_screen.dart";
import "package:expenis_mobile/service/base_service.dart";
import "package:expenis_mobile/service/category_service.dart";
import "package:expenis_mobile/theme.dart";
import "package:expenis_mobile/utils/category_colors.dart";

class CategoryApi {
  int count = 8;
  bool reverse = false;
  int saveStatus = 200;
  String savedColor = categoryColorPalette.first;
  final requests = <RequestOptions>[];

  Map<String, dynamic> category(int id) => {
    "id": id,
    "name": "Category $id",
    "type": "expense",
    "color": id == 1 ? savedColor : categoryColorPalette[(id - 1) % 32],
  };

  void install() {
    final dio = Dio();
    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (request, handler) {
          requests.add(request);
          dynamic body;
          var status = 200;
          if (request.method == "PUT") {
            status = saveStatus;
            if (status == 200 && (request.data as Map).containsKey("color")) {
              savedColor = request.data["color"] as String;
            }
            body = category(1);
          } else if (request.path.endsWith("/categories/1")) {
            body = category(1);
          } else if (request.path.endsWith("/categories")) {
            body = {
              "categories": {
                for (var id = 1; id <= count; id++) "$id": category(id),
              },
            };
          } else if (request.path.endsWith("/tags")) {
            body = {"tags": [], "tag_periods": []};
          } else if (request.path.endsWith("/transactions")) {
            final now = DateTime.now();
            body = {
              "transactions": [
                for (var id = 1; id <= count; id++)
                  {
                    "id": id,
                    "category_id": id,
                    "category": "Category $id",
                    "type": "expense",
                    "account": "Cash",
                    "account_id": 1,
                    "amount": reverse ? id * 100 : (count + 1 - id) * 100,
                    "amount_rubles": reverse
                        ? id * 100
                        : (count + 1 - id) * 100,
                    "currency_code": "RUB",
                    "created_at": DateTime(
                      now.year,
                      now.month,
                      1,
                    ).toIso8601String(),
                  },
              ],
            };
          } else {
            throw StateError("Unexpected request: ${request.path}");
          }
          handler.resolve(
            Response(requestOptions: request, statusCode: status, data: body),
          );
        },
      ),
    );
    BaseService.debugSetDio(dio);
  }
}

Future<void> preview(WidgetTester tester, String name) async {
  if (Platform.environment["COLOR_PREVIEWS"] != "1") return;
  final boundary = tester.renderObject<RenderRepaintBoundary>(
    find.byKey(const ValueKey("preview")),
  );
  await tester.runAsync(() async {
    final image = await boundary.toImage(pixelRatio: 1);
    final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
    await File(
      "/private/tmp/category-$name.png",
    ).writeAsBytes(bytes!.buffer.asUint8List());
    image.dispose();
  });
}

ThemeData previewTheme(ThemeData theme) =>
    Platform.environment["COLOR_PREVIEWS"] == "1"
    ? theme.copyWith(
        textTheme: theme.textTheme.apply(fontFamily: "PreviewSans"),
        primaryTextTheme: theme.primaryTextTheme.apply(
          fontFamily: "PreviewSans",
        ),
      )
    : theme;

Future<void> openEditor(WidgetTester tester, {ThemeData? theme}) async {
  await tester.pumpWidget(
    RepaintBoundary(
      key: const ValueKey("preview"),
      child: MaterialApp(
        theme: previewTheme(theme ?? AppTheme.light),
        home: Builder(
          builder: (context) {
            return Scaffold(
              body: TextButton(
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (_) => const EditCategoryScreen(categoryId: 1),
                  ),
                ),
                child: const Text("Open editor"),
              ),
            );
          },
        ),
      ),
    ),
  );
  await tester.tap(find.text("Open editor"));
  await tester.pumpAndSettle();
}

Future<void> openAnalytics(WidgetTester tester, {bool grouped = false}) async {
  await tester.pumpWidget(
    RepaintBoundary(
      key: const ValueKey("preview"),
      child: MaterialApp(
        theme: previewTheme(AppTheme.light),
        home: TransactionStatsScreen(
          initialEndDate: DateTime.now(),
          initialGroupByMonth: grouped,
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  setUpAll(() async {
    if (Platform.environment["COLOR_PREVIEWS"] != "1") return;
    for (final entry in {
      "PreviewSans": Platform.environment["COLOR_PREVIEW_FONT"]!,
      "MaterialIcons": Platform.environment["COLOR_PREVIEW_ICONS"]!,
    }.entries) {
      final loader = FontLoader(entry.key)
        ..addFont(
          File(
            entry.value,
          ).readAsBytes().then((bytes) => ByteData.sublistView(bytes)),
        );
      await loader.load();
    }
  });
  late CategoryApi api;
  setUp(() {
    api = CategoryApi()..install();
  });
  tearDown(BaseService.debugReset);

  test(
    "category preserves canonical server color and omits unchanged color on save",
    () async {
      final category = Category.fromJson(api.category(1));
      expect(category.displayColor, categoryDisplayColor(api.savedColor));
      await CategoryService().updateCategory(
        category,
        originalColor: category.color,
      );
      expect(api.requests.last.data, isNot(contains("color")));
      api.saveStatus = 422;
      await expectLater(
        CategoryService().updateCategory(
          category,
          originalColor: categoryColorPalette[1],
        ),
        throwsException,
      );
    },
  );

  testWidgets("editor saves selected color and displays it on reopening", (
    tester,
  ) async {
    await openEditor(tester);
    expect(find.byIcon(Icons.check_rounded), findsOneWidget);
    await tester.tap(find.byKey(ValueKey(categoryColorPalette[3])));
    await tester.ensureVisible(find.text("Save Changes"));
    await tester.tap(find.text("Save Changes"));
    await tester.pumpAndSettle();
    expect(api.savedColor, categoryColorPalette[3]);
    await tester.tap(find.text("Open editor"));
    await tester.pumpAndSettle();
    final selected = tester.widget<Semantics>(
      find.byWidgetPredicate(
        (widget) =>
            widget is Semantics && widget.properties.label == "Chart color 4",
      ),
    );
    expect(selected.properties.selected, isTrue);
  });

  testWidgets("cancel leaves server color unchanged", (tester) async {
    await openEditor(tester);
    await tester.tap(find.byKey(ValueKey(categoryColorPalette[3])));
    await tester.pageBack();
    await tester.pumpAndSettle();
    expect(api.requests.where((r) => r.method == "PUT"), isEmpty);
    expect(api.savedColor, categoryColorPalette.first);
  });

  testWidgets("failed save stays open and permits retry", (tester) async {
    await openEditor(tester);
    await tester.tap(find.byKey(ValueKey(categoryColorPalette[3])));
    await tester.ensureVisible(find.text("Save Changes"));
    api.saveStatus = 422;
    await tester.tap(find.text("Save Changes"));
    await tester.pumpAndSettle();
    expect(find.textContaining("Failed to update category"), findsWidgets);
    expect(api.savedColor, categoryColorPalette.first);
    api.saveStatus = 200;
    await tester.tap(find.text("Save Changes"));
    await tester.pumpAndSettle();
    expect(api.savedColor, categoryColorPalette[3]);
  });

  for (final dark in [false, true]) {
    testWidgets("narrow editor palette ${dark ? 'dark' : 'light'}", (
      tester,
    ) async {
      tester.view.physicalSize = const Size(390, 1000);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      await openEditor(
        tester,
        theme: dark ? ThemeData.dark(useMaterial3: true) : AppTheme.light,
      );
      expect(
        find
            .byType(InkWell)
            .evaluate()
            .where((element) => element.widget.key is ValueKey<String>)
            .length,
        32,
      );
      expect(tester.takeException(), isNull);
      await preview(tester, dark ? "editor-dark" : "editor-light");
    });
  }

  for (final count in [7, 8, 33]) {
    testWidgets(
      "analytics uses stored colors and aggregates $count categories",
      (tester) async {
        api.count = count;
        await openAnalytics(tester);
        final pie = tester.widget<PieChart>(find.byType(PieChart));
        expect(pie.data.sections.length, 7);
        expect(
          pie.data.sections.take(6).map((s) => s.color),
          categoryColorPalette.take(6).map(categoryDisplayColor),
        );
        expect(
          pie.data.sections.last.color,
          count == 7
              ? categoryDisplayColor(categoryColorPalette[6])
              : AppTheme.chartOtherColor,
        );
        expect(
          pie.data.sections.fold<double>(0, (sum, s) => sum + s.value),
          count * (count + 1) * 50,
        );
        expect(tester.takeException(), isNull);
        if (count == 8) await preview(tester, "analytics-eight");
      },
    );
  }

  testWidgets(
    "Other highlights members by identity even with duplicate colors",
    (tester) async {
      api.count = 8;
      // A leading category shares the last category's color.
      api.savedColor = categoryColorPalette[7];
      await openAnalytics(tester);
      final pie = tester.widget<PieChart>(find.byType(PieChart));
      pie.data.pieTouchData.touchCallback!(
        FlTapDownEvent(TapDownDetails()),
        PieTouchResponse(PieTouchedSection(pie.data.sections.last, 6, 0, 70)),
      );
      await tester.pumpAndSettle();
      for (final id in [1, 7, 8]) {
        final row = find.byWidgetPredicate(
          (widget) =>
              widget.runtimeType.toString() == "_CategoryShareRow" &&
              (widget as dynamic).label == "Category $id",
        );
        final label = tester.widget<Text>(
          find.descendant(of: row, matching: find.text("Category $id")),
        );
        expect(
          label.style!.fontWeight,
          id == 1 ? FontWeight.w500 : FontWeight.w700,
        );
        final dot = tester.widget<Container>(
          find.descendant(
            of: row,
            matching: find.byWidgetPredicate(
              (widget) =>
                  widget is Container && widget.constraints?.maxWidth == 10,
            ),
          ),
        );
        expect(
          (dot.decoration as BoxDecoration).color,
          categoryDisplayColor(
            id == 1 ? api.savedColor : categoryColorPalette[id - 1],
          ),
        );
      }
    },
  );

  testWidgets("filtering keeps category colors", (tester) async {
    api.count = 7;
    tester.view.physicalSize = const Size(1500, 1400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await openAnalytics(tester);
    await tester.ensureVisible(find.text("Category filter"));
    await tester.tap(find.text("Category filter"));
    await tester.pumpAndSettle();
    final chip = find.widgetWithText(FilterChip, "Category 1");
    await tester.ensureVisible(chip);
    await tester.tap(chip);
    await tester.pumpAndSettle();
    final pie = tester.widget<PieChart>(find.byType(PieChart));
    expect(
      pie.data.sections.map((s) => s.color),
      categoryColorPalette.skip(1).take(6).map(categoryDisplayColor),
    );
  });

  testWidgets(
    "period reload changes rank and remote color without changing identity",
    (tester) async {
      api.count = 7;
      await openAnalytics(tester);
      api.reverse = true;
      api.savedColor = categoryColorPalette[20];
      await tester.tap(find.byTooltip("Previous month"));
      await tester.pumpAndSettle();
      final pie = tester.widget<PieChart>(find.byType(PieChart));
      expect(
        pie.data.sections.last.color,
        categoryDisplayColor(api.savedColor),
      );
      expect(
        pie.data.sections.first.color,
        categoryDisplayColor(categoryColorPalette[6]),
      );
      expect(
        api.requests.where((r) => r.path.endsWith("/categories")).length,
        2,
      );
    },
  );

  testWidgets("monthly stacks and donut use the same saved category colors", (
    tester,
  ) async {
    api.count = 8;
    tester.view.physicalSize = const Size(1500, 1400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await openAnalytics(tester, grouped: true);
    final pie = tester.widget<PieChart>(find.byType(PieChart));
    final bar = tester.widget<BarChart>(find.byType(BarChart));
    final stacks = bar.data.barGroups
        .expand((g) => g.barRods)
        .expand((rod) => rod.rodStackItems)
        .toList();
    expect(stacks.map((s) => s.color), pie.data.sections.map((s) => s.color));
    expect(tester.takeException(), isNull);
    await preview(tester, "analytics-monthly");
  });
}
