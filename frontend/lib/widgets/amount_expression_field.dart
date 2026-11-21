import "package:flutter/material.dart";

import "package:expenis_mobile/utils/amount_expression.dart";
import "package:expenis_mobile/utils/format.dart";
import "package:expenis_mobile/widgets/amount_calculator_keyboard.dart";

class AmountExpressionField extends FormField<AmountExpressionResult> {
  AmountExpressionField({
    super.key,
    required this.controller,
    required this.decoration,
  }) : super(
         initialValue: evaluateAmountExpression(controller.text),
         validator: (_) => evaluateAmountExpression(controller.text).error,
         builder: (state) =>
             (state as _AmountExpressionFieldState)._buildField(),
       );

  final TextEditingController controller;
  final InputDecoration decoration;

  @override
  FormFieldState<AmountExpressionResult> createState() =>
      _AmountExpressionFieldState();
}

class _AmountExpressionFieldState
    extends FormFieldState<AmountExpressionResult> {
  final _focus = FocusNode();
  final _fieldKey = GlobalKey();
  AmountInputScopeState? _scope;
  bool _showValidation = false;

  @override
  AmountExpressionField get widget => super.widget as AmountExpressionField;

  @override
  void initState() {
    super.initState();
    widget.controller.addListener(_changed);
    _focus.addListener(_focusChanged);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _scope = AmountInputScope.maybeOf(context);
  }

  @override
  void didUpdateWidget(covariant AmountExpressionField oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.controller != widget.controller) {
      oldWidget.controller.removeListener(_changed);
      widget.controller.addListener(_changed);
      _changed();
    }
  }

  void _changed() {
    didChange(evaluateAmountExpression(widget.controller.text));
    if (_showValidation) validate();
    if (_focus.hasFocus) _scope?.revealField();
  }

  void _focusChanged() {
    if (_focus.hasFocus) {
      _scope?.showForField(widget.controller, _focus, _fieldKey);
    } else {
      validate();
      _scope?.deactivateField(_focus);
    }
  }

  @override
  bool validate() {
    _showValidation = true;
    return super.validate();
  }

  @override
  void dispose() {
    widget.controller.removeListener(_changed);
    _focus.removeListener(_focusChanged);
    _scope?.deactivateField(_focus);
    _focus.dispose();
    super.dispose();
  }

  Widget _buildField() {
    final result = value ?? evaluateAmountExpression(widget.controller.text);
    final phone =
        MediaQuery.sizeOf(context).shortestSide < 600 && _scope != null;
    final immediateError =
        result.status == AmountExpressionStatus.divisionByZero;
    return TextField(
      key: _fieldKey,
      controller: widget.controller,
      focusNode: _focus,
      keyboardType: phone ? TextInputType.none : TextInputType.text,
      autocorrect: false,
      enableSuggestions: false,
      selectAllOnFocus: false,
      onTap: () {
        if (_focus.hasFocus) {
          _scope?.showForField(widget.controller, _focus, _fieldKey);
        }
      },
      // Touching the calculator is still interacting with this field. Other
      // taps (including touch on mobile) finish input and run validation.
      onTapOutside: (_) => _focus.unfocus(),
      decoration: widget.decoration.copyWith(
        helperText: result.isValid ? "= ${formatAmount(result.amount!)}" : null,
        errorText: immediateError ? result.error : errorText,
      ),
    );
  }
}
