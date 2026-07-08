import 'package:flutter/material.dart';

/// A compact [CircularProgressIndicator] sized for use inside buttons.
///
/// Renders a 20×20 spinner with a stroke width of 2, matching the standard
/// button-inline loading pattern used across form screens.
class AppLoadingSpinner extends StatelessWidget {
  const AppLoadingSpinner({super.key});

  @override
  Widget build(BuildContext context) {
    return const SizedBox(
      width: 20,
      height: 20,
      child: CircularProgressIndicator(strokeWidth: 2),
    );
  }
}
