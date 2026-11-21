import "package:dio/dio.dart";
import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";

import "package:expenis_mobile/screens/create_account_screen.dart";
import "package:expenis_mobile/screens/edit_account_screen.dart";
import "package:expenis_mobile/screens/edit_transaction_screen.dart";
import "package:expenis_mobile/service/base_service.dart";
import "package:expenis_mobile/widgets/amount_expression_field.dart";

void main() {
  late List<RequestOptions> writes;
  late double accountAmount;
  late double transactionAmount;
  late bool failNextWrite;
  final account = <String, dynamic>{
    "id": 1,
    "user_id": 1,
    "name": "Cash",
    "amount": 1000.0,
    "amount_rubles": 1000.0,
    "currency_code": "RUB",
  };
  final transaction = <String, dynamic>{
    "id": 1,
    "account": "Cash",
    "account_id": 1,
    "category_id": 1,
    "category": "Cafe",
    "type": "expense",
    "amount": 10.0,
    "amount_rubles": 10.0,
    "currency_code": "RUB",
    "description": "Lunch",
    "tags": <String>[],
    "created_at": "2026-11-21T12:00:00Z",
  };

  setUp(() {
    writes = [];
    accountAmount = 1000;
    transactionAmount = 10;
    failNextWrite = false;
    final dio = Dio();
    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          final path = options.uri.path;
          if (options.method != "GET") {
            writes.add(options);
            if (failNextWrite) {
              failNextWrite = false;
              handler.reject(
                DioException(
                  requestOptions: options,
                  type: DioExceptionType.connectionError,
                ),
              );
              return;
            }
            final data = options.data as Map<String, dynamic>;
            if (path.contains("accounts/account")) {
              accountAmount = (data["amount"] as num).toDouble();
            } else if (path.contains("transactions")) {
              transactionAmount = (data["amount"] as num).toDouble();
            }
          }
          final Object data;
          if (path == "/api/accounts") {
            data = {
              "accounts": {
                "1": {...account, "amount": accountAmount},
              },
              "total_amount_rubles": accountAmount,
            };
          } else if (path == "/api/categories") {
            data = {
              "categories": {
                "1": {
                  "id": 1,
                  "name": "Cafe",
                  "type": "expense",
                  "color": "#4E79A7",
                },
              },
            };
          } else if (path == "/api/tags") {
            data = {"tags": <String>[]};
          } else if (path == "/api/currency/codes") {
            data = {
              "codes": {"RUB": {}},
            };
          } else if (path.contains("accounts/account")) {
            data = {...account, "amount": accountAmount};
          } else if (path.contains("transactions")) {
            data = {...transaction, "amount": transactionAmount};
          } else {
            throw StateError("Unexpected request: $path");
          }
          handler.resolve(
            Response(requestOptions: options, statusCode: 200, data: data),
          );
        },
      ),
    );
    BaseService.debugSetDio(dio);
  });
  tearDown(BaseService.debugReset);

  Future<void> mount(WidgetTester tester, Widget screen) async {
    tester.view.physicalSize = const Size(1200, 1200);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(
      MaterialApp(
        home: Builder(
          builder: (context) => Scaffold(
            body: TextButton(
              onPressed: () => Navigator.of(
                context,
              ).push(MaterialPageRoute<void>(builder: (_) => screen)),
              child: const Text("Open"),
            ),
          ),
        ),
      ),
    );
    await tester.tap(find.text("Open"));
    await tester.pumpAndSettle();
  }

  Finder field(String label) => find.byWidgetPredicate(
    (widget) => widget is TextField && widget.decoration?.labelText == label,
  );
  Future<void> save(WidgetTester tester, String label) async {
    await tester.ensureVisible(find.text(label));
    await tester.pumpAndSettle();
    await tester.tap(find.text(label));
    await tester.pumpAndSettle();
  }

  testWidgets("initial balance submits rounded number and no expression", (
    tester,
  ) async {
    await mount(tester, const CreateAccountScreen());
    await tester.enterText(field("Account Name"), "Cash");
    await tester.enterText(field("Initial Balance"), "1000/3");
    await tester.enterText(field("Currency Code"), "RUB");
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(ListTile, "RUB"));
    await tester.pumpAndSettle();
    await save(tester, "Create Account");
    expect(writes.single.data, {
      "name": "Cash",
      "amount": 333.33,
      "currency_code": "RUB",
    });
    expect(find.byType(CreateAccountScreen), findsNothing);
  });

  testWidgets(
    "balance edit sends target balance and reopens as stored number",
    (tester) async {
      await mount(tester, const EditAccountScreen(accountId: 1));
      expect(
        tester
            .widget<AmountExpressionField>(find.byType(AmountExpressionField))
            .controller
            .text,
        "1000.0",
      );
      await tester.enterText(field("Balance"), "1000-250");
      await save(tester, "Save Changes");
      expect(writes.single.data["amount"], 750);
      await tester.tap(find.text("Open"));
      await tester.pumpAndSettle();
      expect(
        tester
            .widget<AmountExpressionField>(find.byType(AmountExpressionField))
            .controller
            .text,
        "750.0",
      );
    },
  );

  for (final editing in [false, true]) {
    for (final expression in ["1.005", "100-100", "-100+20"]) {
      testWidgets(
        "transaction ${editing ? 'edit' : 'create'} submits $expression",
        (tester) async {
          await mount(
            tester,
            EditTransactionScreen(transactionId: editing ? 1 : null),
          );
          if (!editing) {
            final dropdowns = find.byType(DropdownButtonFormField<int>);
            await tester.tap(dropdowns.first);
            await tester.pumpAndSettle();
            await tester.tap(find.text("Cash").last);
            await tester.pumpAndSettle();
            await tester.tap(dropdowns.last);
            await tester.pumpAndSettle();
            await tester.tap(find.text("Cafe").last);
            await tester.pumpAndSettle();
          }
          await tester.enterText(field("Amount"), expression);
          await save(tester, editing ? "Save Changes" : "Add Transaction");
          expect(writes.single.method, editing ? "PUT" : "POST");
          expect(writes.single.data["amount"], switch (expression) {
            "1.005" => 1.01,
            "100-100" => 0,
            _ => -80,
          });
          expect(writes.single.data["amount"], isA<num>());
        },
      );
    }
  }

  testWidgets(
    "invalid balance never sends a write; network failure preserves expression for retry",
    (tester) async {
      await mount(tester, const EditAccountScreen(accountId: 1));
      await tester.enterText(field("Balance"), "100+");
      await save(tester, "Save Changes");
      expect(writes, isEmpty);
      await tester.enterText(field("Balance"), "100/3");
      failNextWrite = true;
      await save(tester, "Save Changes");
      expect(writes, hasLength(1));
      expect(
        tester
            .widget<AmountExpressionField>(find.byType(AmountExpressionField))
            .controller
            .text,
        "100/3",
      );
      await save(tester, "Save Changes");
      expect(writes, hasLength(2));
      expect(writes.last.data["amount"], 33.33);
    },
  );

  testWidgets(
    "invalid transaction never sends a write and saved expression is not reloaded",
    (tester) async {
      await mount(tester, const EditTransactionScreen(transactionId: 1));
      await tester.enterText(field("Amount"), "100/0");
      await save(tester, "Save Changes");
      expect(writes, isEmpty);
      await tester.enterText(field("Amount"), "120+80");
      await save(tester, "Save Changes");
      await tester.tap(find.text("Open"));
      await tester.pumpAndSettle();
      expect(
        tester
            .widget<AmountExpressionField>(find.byType(AmountExpressionField))
            .controller
            .text,
        "200.0",
      );
    },
  );
}
