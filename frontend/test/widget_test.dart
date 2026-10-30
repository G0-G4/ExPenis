import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";
import "package:shared_preferences/shared_preferences.dart";
import "package:expenis_mobile/main.dart";
import "package:expenis_mobile/service/settings_service.dart";
import "package:expenis_mobile/service/telemetry_service.dart";

void main() {
  testWidgets("unauthenticated app opens login with collection disabled", (
    tester,
  ) async {
    SettingsService.debugReset();
    SharedPreferences.setMockInitialValues({});
    TelemetryService.instance = TelemetryService();
    await tester.pumpWidget(const MyApp());
    await tester.pumpAndSettle();
    expect(find.byType(TextField), findsNWidgets(2));
    expect(TelemetryService.instance.queued, 0);
    expect(tester.takeException(), isNull);
  });
}
