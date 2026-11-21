import "dart:async";
import "dart:convert";

import "package:dio/dio.dart";
import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";
import "package:shared_preferences/shared_preferences.dart";

import "package:expenis_mobile/main.dart";
import "package:expenis_mobile/screens/transaction_screen.dart";
import "package:expenis_mobile/service/base_service.dart";
import "package:expenis_mobile/service/settings_service.dart";
import "package:expenis_mobile/widgets/personal_greeting_banner.dart";

import "helpers/greeting_http.dart";

void main() {
  late GreetingHttp http;
  setUp(() async {
    SettingsService.debugReset();
    SharedPreferences.setMockInitialValues({"access_token": "test-token"});
    await SettingsService.getInstance();
    http = GreetingHttp()..greeting = greetingJson("Поздравляю 🎉\nHello");
    BaseService.debugSetDio(
      Dio(BaseOptions(validateStatus: (s) => s! < 500))
        ..httpClientAdapter = http,
    );
  });
  tearDown(BaseService.debugReset);

  Future<void> mount(
    WidgetTester tester, {
    bool active = true,
    int revision = 0,
  }) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: PersonalGreetingBanner(
            active: active,
            refreshRevision: revision,
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets(
    "shows plain multiline text, closes, then displays a new assignment",
    (tester) async {
      await mount(tester);
      expect(find.text("Поздравляю 🎉\nHello"), findsOneWidget);
      await tester.tap(find.byTooltip("Close greeting"));
      await tester.pumpAndSettle();
      expect(find.byType(Card), findsNothing);
      expect(
        http.requests.where((r) => r.method == "POST").single.path,
        endsWith("/assignment-A/dismiss"),
      );
      http.greeting = greetingJson("Поздравляю 🎉\nHello", id: "assignment-B");
      await mount(tester, revision: 1);
      expect(find.text("Поздравляю 🎉\nHello"), findsOneWidget);
    },
  );

  testWidgets("null greeting takes no space and inactive tabs do not load", (
    tester,
  ) async {
    http.greeting = null;
    await mount(tester);
    expect(tester.getSize(find.byType(PersonalGreetingBanner)).height, 0);
    await mount(tester, active: false);
    final reads = http.reads;
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    await tester.pumpAndSettle();
    expect(http.reads, reads);
    http.greeting = greetingJson("Returned");
    await mount(tester);
    expect(find.text("Returned"), findsOneWidget);
    expect(http.reads, reads + 1);
  });

  testWidgets("refresh and resume remove dismissal from another client", (
    tester,
  ) async {
    await mount(tester);
    http.greeting = null;
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    await tester.pumpAndSettle();
    expect(find.byType(Card), findsNothing);
    expect(http.reads, 2);
    http.greeting = greetingJson("Again");
    await mount(tester, revision: 1);
    expect(find.text("Again"), findsOneWidget);
  });

  testWidgets("failed read removes old text and offers retry", (tester) async {
    await mount(tester);
    http.readStatus = 500;
    await mount(tester, revision: 1);
    expect(find.text("Поздравляю 🎉\nHello"), findsNothing);
    expect(find.text("Could not load greeting."), findsOneWidget);
    http.readStatus = 200;
    await tester.tap(find.text("Retry"));
    await tester.pumpAndSettle();
    expect(find.text("Поздравляю 🎉\nHello"), findsOneWidget);
  });

  testWidgets("failed dismissal retains text and retries", (tester) async {
    await mount(tester);
    http.dismissStatus = 500;
    await tester.tap(find.byTooltip("Close greeting"));
    await tester.pumpAndSettle();
    expect(find.text("Поздравляю 🎉\nHello"), findsOneWidget);
    http.dismissStatus = 204;
    await tester.tap(find.text("Retry"));
    await tester.pumpAndSettle();
    expect(find.byType(Card), findsNothing);
  });

  testWidgets("ignores a stale read after a newer refresh", (tester) async {
    final pending = Completer<ResponseBody>();
    http.pendingRead = pending;
    await mount(tester);
    http.greeting = greetingJson("New", id: "B");
    await mount(tester, revision: 1);
    expect(find.text("New"), findsOneWidget);
    pending.complete(GreetingHttp.json({"greeting": greetingJson("Stale")}));
    await tester.pumpAndSettle();
    expect(find.text("New"), findsOneWidget);
    expect(find.text("Stale"), findsNothing);
  });

  testWidgets("late dismissal response preserves a replacement", (
    tester,
  ) async {
    await mount(tester);
    final pending = Completer<ResponseBody>();
    http.pendingDismiss = pending;
    await tester.tap(find.byTooltip("Close greeting"));
    await tester.pumpAndSettle();
    http.greeting = greetingJson("New", id: "B");
    await mount(tester, revision: 1);
    expect(find.text("New"), findsOneWidget);
    pending.complete(GreetingHttp.json(null, 204));
    await tester.pumpAndSettle();
    expect(find.text("New"), findsOneWidget);
  });

  testWidgets(
    "session change clears text and rejects previous user's response",
    (tester) async {
      final pending = Completer<ResponseBody>();
      http.pendingRead = pending;
      await mount(tester);
      final settings = await SettingsService.getInstance();
      await settings.clearAuth();
      await tester.pumpAndSettle();
      pending.complete(
        GreetingHttp.json({"greeting": greetingJson("Other user")}),
      );
      await tester.pumpAndSettle();
      expect(find.text("Other user"), findsNothing);
      expect(find.byType(Card), findsNothing);
      http.greeting = greetingJson("Current user");
      await settings.setAccessToken("new-token");
      await tester.pumpAndSettle();
      expect(find.text("Current user"), findsOneWidget);
    },
  );

  testWidgets(
    "account switch invalidates reads while same-user token rotation preserves state",
    (tester) async {
      String token(String subject, int version) =>
          "header.${base64Url.encode(utf8.encode(jsonEncode({"sub": subject, "version": version})))}.signature";
      final settings = await SettingsService.getInstance();
      await settings.setAccessToken(token("alice", 1));
      final pending = Completer<ResponseBody>();
      http.pendingRead = pending;
      await mount(tester);
      http.greeting = greetingJson("Bob greeting", id: "B");
      await settings.setAccessToken(token("bob", 1));
      await tester.pumpAndSettle();
      pending.complete(
        GreetingHttp.json({"greeting": greetingJson("Alice greeting")}),
      );
      await tester.pumpAndSettle();
      expect(find.text("Bob greeting"), findsOneWidget);
      expect(find.text("Alice greeting"), findsNothing);
      final reads = http.reads;
      final revision = SettingsService.sessionRevision.value;
      await settings.setAccessToken(token("bob", 2));
      await tester.pumpAndSettle();
      expect(SettingsService.sessionRevision.value, revision);
      expect(http.reads, reads);
      expect(find.text("Bob greeting"), findsOneWidget);
    },
  );

  testWidgets("expires while open and cancels timer on dispose", (
    tester,
  ) async {
    http.greeting = greetingJson(
      "Timed",
      expiry: DateTime.now().toUtc().add(const Duration(seconds: 3)),
    );
    await mount(tester);
    expect(find.text("Timed"), findsOneWidget);
    await tester.pump(const Duration(seconds: 4));
    expect(find.text("Timed"), findsNothing);
    http.greeting = greetingJson(
      "Later",
      expiry: DateTime.now().toUtc().add(const Duration(days: 1)),
    );
    await mount(tester, revision: 1);
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump(const Duration(days: 2));
    expect(tester.takeException(), isNull);
  });

  testWidgets(
    "long greeting fits a narrow screen with large text and an empty list",
    (tester) async {
      tester.view.physicalSize = const Size(320, 640);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final text = List.filled(100, "Привет! 🎉\n").join();
      http.greeting = greetingJson(text);
      await tester.pumpWidget(
        MaterialApp(
          builder: (context, child) => MediaQuery(
            data: MediaQuery.of(
              context,
            ).copyWith(textScaler: TextScaler.linear(2)),
            child: child!,
          ),
          home: const TransactionScreen(),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text(text), findsOneWidget);
      expect(find.text("No transactions"), findsOneWidget);
      await tester.drag(
        find.descendant(
          of: find.byType(PersonalGreetingBanner),
          matching: find.byType(SingleChildScrollView),
        ),
        const Offset(0, -500),
      );
      await tester.pumpAndSettle();
      expect(find.byTooltip("Close greeting").hitTestable(), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    "transaction refresh loads greeting and errors leave transactions usable",
    (tester) async {
      http.readStatus = 500;
      await tester.pumpWidget(const MaterialApp(home: TransactionScreen()));
      await tester.pumpAndSettle();
      expect(find.text("No transactions"), findsOneWidget);
      expect(find.text("Could not load greeting."), findsOneWidget);
      http.readStatus = 200;
      await tester.tap(find.byTooltip("Refresh"));
      await tester.pumpAndSettle();
      expect(find.text("Поздравляю 🎉\nHello"), findsOneWidget);
      expect(find.text("No transactions"), findsOneWidget);
    },
  );

  testWidgets("home tab navigation refreshes greeting only for transactions", (
    tester,
  ) async {
    await tester.pumpWidget(const MaterialApp(home: HomeScreen()));
    await tester.pumpAndSettle();
    expect(find.text("Поздравляю 🎉\nHello"), findsOneWidget);
    await tester.tap(find.text("Accounts").last);
    await tester.pumpAndSettle();
    expect(find.text("Поздравляю 🎉\nHello"), findsNothing);
    http.greeting = greetingJson("Welcome back");
    await tester.tap(find.text("Transactions").last);
    await tester.pumpAndSettle();
    expect(find.text("Welcome back"), findsOneWidget);
    await tester.tap(find.text("Categories").last);
    await tester.pumpAndSettle();
    expect(find.text("Welcome back"), findsNothing);
    expect(tester.takeException(), isNull);
  });
}
