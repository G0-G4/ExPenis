import "package:flutter/material.dart";

import "package:expenis_mobile/utils/amount_expression.dart";
import "package:expenis_mobile/utils/format.dart";

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
    if (_focus.hasFocus) _revealField();
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
    if (_focus.hasFocus) _revealField();
  }

  void _focusChanged() {
    if (_focus.hasFocus) {
      _revealField();
    } else {
      validate();
    }
  }

  void _revealField() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || !_focus.hasFocus) return;
      final fieldContext = _fieldKey.currentContext;
      if (fieldContext != null) {
        Scrollable.ensureVisible(fieldContext, alignment: 0.5);
      }
    });
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
    _focus.dispose();
    super.dispose();
  }

  Widget _buildField() {
    final result = value ?? evaluateAmountExpression(widget.controller.text);
    final immediateError =
        result.status == AmountExpressionStatus.divisionByZero;
    return TextField(
      key: _fieldKey,
      controller: widget.controller,
      focusNode: _focus,
      keyboardType: TextInputType.text,
      textInputAction: TextInputAction.done,
      onEditingComplete: () => _focus.unfocus(),
      autocorrect: false,
      enableSuggestions: false,
      selectAllOnFocus: false,
      onTapOutside: (_) => _focus.unfocus(),
      decoration: widget.decoration.copyWith(
        helperText: result.isValid ? "= ${formatAmount(result.amount!)}" : null,
        errorText: immediateError ? result.error : errorText,
      ),
    );
  }
}
