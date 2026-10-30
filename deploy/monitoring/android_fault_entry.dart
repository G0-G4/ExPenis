// Test-only entrypoint for an isolated emulator APK or Web bundle. Never publish.
import "dart:async";
import "package:flutter/foundation.dart";
import "package:flutter/widgets.dart";
import "package:expenis_mobile/main.dart" as application;

void main() {
  application.main();
  // Schedule from the application's frame callback so runtime faults execute
  // in its guarded zone, just like callbacks from normal UI actions.
  WidgetsBinding.instance.addPostFrameCallback((_) {
    Timer(const Duration(seconds: 8), () {
      FlutterError.reportError(FlutterErrorDetails(
        exception: StateError("synthetic_framework"),
        stack: StackTrace.current,
      ));
    });
    Timer(const Duration(seconds: 9), () {
      throw StateError("synthetic_unhandled");
    });
  });
}
