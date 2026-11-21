import "package:flutter/foundation.dart";
import "package:flutter/material.dart";
import "package:flutter/services.dart";
import "package:flutter_test/flutter_test.dart";

import "package:expenis_mobile/utils/amount_expression.dart";
import "package:expenis_mobile/widgets/amount_expression_field.dart";

void main() {
  late TextEditingController controller;
  late GlobalKey<FormState> form;
  late List<double> saved;

  setUp(() {
    controller = TextEditingController();
    form = GlobalKey<FormState>();
    saved = [];
  });

  Future<void> mount(
    WidgetTester tester, {
    Size size = const Size(1000, 900),
    double scale = 1,
  }) async {
    tester.view.physicalSize = size;
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(
      MaterialApp(
        builder: (context, child) => MediaQuery(
          data: MediaQuery.of(
            context,
          ).copyWith(textScaler: TextScaler.linear(scale)),
          child: child!,
        ),
        home: Scaffold(
          body: Form(
            key: form,
            child: ListView(
              children: [
                const SizedBox(height: 40),
                AmountExpressionField(
                  controller: controller,
                  decoration: const InputDecoration(
                    labelText: "Amount",
                    suffixText: "RUB",
                  ),
                ),
                const TextField(
                  decoration: InputDecoration(labelText: "Description"),
                ),
                FilledButton(
                  onPressed: () {
                    if (form.currentState!.validate()) {
                      saved.add(
                        evaluateAmountExpression(controller.text).amount!,
                      );
                    }
                  },
                  child: const Text("Save"),
                ),
              ],
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  Finder amount() => find.byType(TextField).first;

  testWidgets("preview preserves expression, currency and submitted rounding", (
    tester,
  ) async {
    await mount(tester);
    await tester.enterText(amount(), "1.005");
    await tester.pump();
    expect(controller.text, "1.005");
    expect(find.text("= 1.01"), findsOneWidget);
    expect(find.text("RUB"), findsOneWidget);
    await tester.tap(find.text("Save"));
    await tester.pump();
    expect(saved, [1.01]);
    await tester.pumpWidget(const SizedBox());
    controller.dispose();
  });

  testWidgets(
    "incomplete input waits for blur, submit rejects stale result, correction clears error",
    (tester) async {
      await mount(tester);
      await tester.enterText(amount(), "50");
      await tester.enterText(amount(), "100+");
      await tester.pump();
      expect(find.text("= 50"), findsNothing);
      expect(find.text("Please complete the expression"), findsNothing);
      await tester.tap(find.text("Save"));
      await tester.pumpAndSettle();
      expect(saved, isEmpty);
      expect(find.text("Please complete the expression"), findsOneWidget);
      await tester.enterText(amount(), "100/2");
      await tester.pumpAndSettle();
      expect(find.text("Please complete the expression"), findsNothing);
      expect(find.text("= 50"), findsOneWidget);
      await tester.enterText(amount(), "100/0");
      await tester.pump();
      expect(find.text("Cannot divide by zero"), findsOneWidget);
      await tester.tap(find.byType(TextField).last);
      await tester.pump();
      expect(form.currentState!.validate(), isFalse);
      await tester.pumpWidget(const SizedBox());
      controller.dispose();
    },
  );

  testWidgets("zero division is immediate before first blur", (tester) async {
    await mount(tester);
    await tester.enterText(amount(), "100/(2-2)");
    await tester.pump();
    expect(find.text("Cannot divide by zero"), findsOneWidget);
    await tester.enterText(amount(), "100/2");
    await tester.pumpAndSettle();
    expect(find.text("Cannot divide by zero"), findsNothing);
    await tester.pumpWidget(const SizedBox());
    controller.dispose();
  });

  testWidgets("phone requests native text input and Done does not submit", (
    tester,
  ) async {
    await mount(tester, size: const Size(390, 844));
    await tester.tap(amount());
    await tester.enterText(amount(), "120+80");
    await tester.pumpAndSettle();
    expect(tester.widget<TextField>(amount()).keyboardType, TextInputType.text);
    expect(tester.testTextInput.isVisible, isTrue);
    expect(find.text("= 200"), findsOneWidget);
    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.pumpAndSettle();
    expect(controller.text, "120+80");
    expect(saved, isEmpty);
    expect(tester.widget<TextField>(amount()).focusNode!.hasFocus, isFalse);
    await tester.pumpWidget(const SizedBox());
    controller.dispose();
  });

  testWidgets("native selection replacement and deletion recompute result", (
    tester,
  ) async {
    debugDefaultTargetPlatformOverride = TargetPlatform.macOS;
    addTearDown(() => debugDefaultTargetPlatformOverride = null);
    await mount(tester, size: const Size(390, 844));
    await tester.enterText(amount(), "100/3");
    await tester.sendKeyDownEvent(LogicalKeyboardKey.metaLeft);
    await tester.sendKeyEvent(LogicalKeyboardKey.keyA);
    await tester.sendKeyUpEvent(LogicalKeyboardKey.metaLeft);
    await tester.pumpAndSettle();
    expect(
      controller.selection,
      const TextSelection(baseOffset: 0, extentOffset: 5),
    );
    tester.testTextInput.updateEditingValue(
      const TextEditingValue(
        text: "2/4",
        selection: TextSelection.collapsed(offset: 3),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text("= 0.50"), findsOneWidget);
    tester.testTextInput.updateEditingValue(
      const TextEditingValue(
        text: "2/",
        selection: TextSelection.collapsed(offset: 2),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text("= 0.50"), findsNothing);
    await tester.tap(find.byType(TextField).last);
    await tester.pumpAndSettle();
    expect(find.text("Please complete the expression"), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
    controller.dispose();
    debugDefaultTargetPlatformOverride = null;
  });

  testWidgets(
    "preview remains visible above native keyboard inset after rotation",
    (tester) async {
      await mount(tester, size: const Size(390, 844), scale: 2);
      tester.view.viewInsets = const FakeViewPadding(bottom: 300);
      addTearDown(tester.view.resetViewInsets);
      await tester.enterText(amount(), "100/3");
      await tester.pumpAndSettle();
      expect(tester.getBottomLeft(find.text("= 33.33")).dy, lessThan(544));
      tester.view.physicalSize = const Size(844, 390);
      tester.view.viewInsets = const FakeViewPadding(bottom: 180);
      await tester.pumpAndSettle();
      expect(
        tester.getBottomLeft(find.text("= 33.33")).dy,
        lessThanOrEqualTo(210),
      );
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
      controller.dispose();
    },
  );
}
