import "package:flutter/material.dart";

/// One keypad for both native phone apps and phone browsers.
class AmountCalculatorKeyboard extends StatelessWidget {
  const AmountCalculatorKeyboard({
    super.key,
    required this.controller,
    required this.onDone,
  });

  final TextEditingController controller;
  final VoidCallback onDone;

  void _input(String key) {
    final value = controller.value;
    final selection = value.selection;

    var start = selection.isValid ? selection.start : value.text.length;
    final end = selection.isValid ? selection.end : value.text.length;
    var replacement = key;
    if (key == "⌫") {
      replacement = "";
      if (start == end && start > 0) {
        start--;
        // Do not leave an unpaired UTF-16 surrogate in pasted text.
        if (start > 0 &&
            (value.text.codeUnitAt(start) & 0xfc00) == 0xdc00 &&
            (value.text.codeUnitAt(start - 1) & 0xfc00) == 0xd800) {
          start--;
        }
      }
    }
    controller.value = TextEditingValue(
      text: value.text.replaceRange(start, end, replacement),
      selection: TextSelection.collapsed(offset: start + replacement.length),
    );
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    const portraitRows = [
      ["7", "8", "9", "÷", "("],
      ["4", "5", "6", "×", ")"],
      ["1", "2", "3", "−", "⌫"],
      ["0", ".", "+", "Done"],
    ];
    final landscape =
        MediaQuery.sizeOf(context).width > MediaQuery.sizeOf(context).height;
    final rows = landscape
        ? [
            [...portraitRows[0], ...portraitRows[1]],
            [...portraitRows[2], ...portraitRows[3]],
          ]
        : portraitRows;
    return TextFieldTapRegion(
      child: ExcludeFocus(
        child: Material(
          elevation: 6,
          color: colors.surfaceContainer,
          child: SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.all(4),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  for (final row in rows)
                    Row(
                      children: [
                        for (final key in row)
                          Expanded(
                            flex: key == "Done" ? 2 : 1,
                            child: Padding(
                              padding: const EdgeInsets.all(2),
                              child: Semantics(
                                button: true,
                                child: Material(
                                  color: key == "Done"
                                      ? colors.primaryContainer
                                      : colors.surface,
                                  borderRadius: BorderRadius.circular(12),
                                  child: InkWell(
                                    key: ValueKey("calculator-$key"),
                                    // Keep both native and browser input focus on the amount.
                                    canRequestFocus: false,
                                    borderRadius: BorderRadius.circular(12),
                                    onTap: key == "Done"
                                        ? onDone
                                        : () => _input(key),
                                    child: ConstrainedBox(
                                      constraints: const BoxConstraints(
                                        minWidth: 48,
                                        minHeight: 48,
                                      ),
                                      child: Center(
                                        child: Text(
                                          key,
                                          style: Theme.of(context)
                                              .textTheme
                                              .labelLarge
                                              ?.copyWith(
                                                color: key == "Done"
                                                    ? colors.onPrimaryContainer
                                                    : colors.onSurface,
                                              ),
                                          semanticsLabel: switch (key) {
                                            "⌫" => "Delete",
                                            "÷" => "Divide",
                                            "×" => "Multiply",
                                            "−" => "Subtract",
                                            "+" => "Add",
                                            "(" => "Open parenthesis",
                                            ")" => "Close parenthesis",
                                            "." => "Decimal separator",
                                            _ => key,
                                          },
                                        ),
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                            ),
                          ),
                      ],
                    ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Reserves real layout space for the keypad instead of covering the form.
class AmountInputScope extends StatefulWidget {
  const AmountInputScope({super.key, required this.child});
  final Widget child;

  @override
  State<AmountInputScope> createState() => AmountInputScopeState();

  static AmountInputScopeState? maybeOf(BuildContext context) =>
      context.dependOnInheritedWidgetOfExactType<_AmountInputHost>()?.state;
}

class AmountInputScopeState extends State<AmountInputScope> {
  TextEditingController? _controller;
  FocusNode? _focus;
  GlobalKey? _fieldKey;

  void showForField(
    TextEditingController controller,
    FocusNode focus,
    GlobalKey fieldKey,
  ) {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || !focus.hasFocus) return;
      setState(() {
        _controller = controller;
        _focus = focus;
        _fieldKey = fieldKey;
      });
      revealField();
    });
  }

  void deactivateField(FocusNode focus) {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || !identical(_focus, focus)) return;
      setState(() {
        _controller = null;
        _focus = null;
        _fieldKey = null;
      });
    });
  }

  void revealField() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || _focus?.hasFocus != true) return;
      final fieldContext = _fieldKey?.currentContext;
      if (fieldContext != null) {
        Scrollable.ensureVisible(fieldContext, alignment: 0.5);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final phone = MediaQuery.sizeOf(context).shortestSide < 600;
    final open = phone && _focus?.hasFocus == true;
    if (open) revealField();
    return _AmountInputHost(
      state: this,
      child: PopScope(
        canPop: !open,
        onPopInvokedWithResult: (didPop, result) {
          if (!didPop && open) _focus?.unfocus();
        },
        child: Column(
          children: [
            Expanded(child: widget.child),
            if (open)
              AmountCalculatorKeyboard(
                controller: _controller!,
                onDone: () => _focus?.unfocus(),
              ),
          ],
        ),
      ),
    );
  }
}

class _AmountInputHost extends InheritedWidget {
  const _AmountInputHost({required this.state, required super.child});
  final AmountInputScopeState state;

  @override
  bool updateShouldNotify(_AmountInputHost oldWidget) => false;
}
