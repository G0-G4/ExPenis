import "package:flutter/foundation.dart";
import "package:flutter/material.dart";
import "package:flutter/services.dart";
import "package:flutter_test/flutter_test.dart";

import "package:expenis_mobile/utils/amount_expression.dart";
import "package:expenis_mobile/widgets/amount_calculator_keyboard.dart";
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
          body: AmountInputScope(
            child: Form(
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
      ),
    );
    await tester.pumpAndSettle();
  }

  Finder amount() => find.byType(TextField).first;
  Finder key(String value) => find.byKey(ValueKey("calculator-$value"));

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
    expect(find.byType(AmountCalculatorKeyboard), findsNothing);
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

  testWidgets(
    "phone keypad inserts at caret, replaces selection, deletes and keeps focus",
    (tester) async {
      await mount(tester, size: const Size(390, 844));
      await tester.tap(amount());
      await tester.pumpAndSettle();
      expect(find.byType(AmountCalculatorKeyboard), findsOneWidget);
      expect(
        tester.widget<TextField>(amount()).keyboardType,
        TextInputType.none,
      );
      for (final value in [
        "7",
        "8",
        "9",
        "÷",
        "(",
        "×",
        ")",
        "−",
        "+",
        ".",
        "⌫",
        "Done",
      ]) {
        expect(key(value), findsOneWidget);
      }
      controller.value = const TextEditingValue(
        text: "12+3",
        selection: TextSelection.collapsed(offset: 2),
      );
      await tester.tap(key("0"));
      await tester.pump();
      expect(controller.text, "120+3");
      controller.selection = const TextSelection(
        baseOffset: 0,
        extentOffset: 3,
      );
      await tester.tap(key("4"));
      await tester.pump();
      expect(controller.text, "4+3");
      expect(tester.widget<TextField>(amount()).focusNode!.hasFocus, isTrue);
      controller.selection = const TextSelection(
        baseOffset: 1,
        extentOffset: 3,
      );
      await tester.tap(key("⌫"));
      await tester.pump();
      expect(controller.text, "4");
      await tester.tap(key("⌫"));
      await tester.pump();
      expect(controller.text, "");
      await tester.tap(key("⌫"));
      await tester.pump();
      expect(controller.text, "");
      controller.text = "120+80";
      await tester.tap(key("Done"));
      await tester.pumpAndSettle();
      expect(find.byType(AmountCalculatorKeyboard), findsNothing);
      expect(controller.text, "120+80");
      expect(saved, isEmpty);
      await tester.pumpWidget(const SizedBox());
      controller.dispose();
    },
  );

  testWidgets("phone focus switch, back, resize, landscape and text scaling", (
    tester,
  ) async {
    await mount(tester, size: const Size(844, 390), scale: 2);
    await tester.tap(amount());
    await tester.pumpAndSettle();
    controller.text = "100/3";
    await tester.pumpAndSettle();
    final preview = find.text("= 33.33");
    expect(preview, findsOneWidget);
    expect(
      tester.getBottomLeft(preview).dy,
      lessThan(tester.getTopLeft(find.byType(AmountCalculatorKeyboard)).dy),
    );
    expect(tester.takeException(), isNull);
    await tester.binding.handlePopRoute();
    await tester.pumpAndSettle();
    expect(find.byType(AmountCalculatorKeyboard), findsNothing);
    await tester.tap(amount());
    await tester.pumpAndSettle();
    // Scroll the remaining form into view while the keyboard is open.
    await tester.ensureVisible(find.byType(TextField).last);
    await tester.pumpAndSettle();
    await tester.tap(find.byType(TextField).last);
    await tester.pumpAndSettle();
    expect(find.byType(AmountCalculatorKeyboard), findsNothing);
    await tester.ensureVisible(amount());
    await tester.pumpAndSettle();
    await tester.tap(amount());
    await tester.pumpAndSettle();
    tester.view.physicalSize = const Size(1000, 900);
    await tester.pumpAndSettle();
    expect(find.byType(AmountCalculatorKeyboard), findsNothing);
    expect(tester.widget<TextField>(amount()).keyboardType, TextInputType.text);
    await tester.enterText(amount(), "(120+80)/2");
    await tester.sendKeyEvent(LogicalKeyboardKey.end);
    await tester.pump();
    expect(controller.text, "(120+80)/2");
    expect(find.text("= 100"), findsOneWidget);
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
    controller.dispose();
  });
  testWidgets(
    "phone physical select-all keeps selection for keypad replacement",
    (tester) async {
      debugDefaultTargetPlatformOverride = TargetPlatform.macOS;
      addTearDown(() => debugDefaultTargetPlatformOverride = null);
      await mount(tester, size: const Size(390, 844));
      await tester.tap(amount());
      await tester.pumpAndSettle();
      controller.value = const TextEditingValue(
        text: "100/3",
        selection: TextSelection.collapsed(offset: 5),
      );
      await tester.pumpAndSettle();
      await tester.sendKeyDownEvent(LogicalKeyboardKey.metaLeft);
      await tester.sendKeyEvent(LogicalKeyboardKey.keyA);
      await tester.sendKeyUpEvent(LogicalKeyboardKey.metaLeft);
      await tester.pumpAndSettle();
      expect(
        controller.selection,
        const TextSelection(baseOffset: 0, extentOffset: 5),
      );
      await tester.tap(key("2"));
      await tester.pumpAndSettle();
      expect(controller.text, "2");
      await tester.pumpWidget(const SizedBox());
      controller.dispose();
      debugDefaultTargetPlatformOverride = null;
    },
  );
}
