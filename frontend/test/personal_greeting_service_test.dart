import "package:dio/dio.dart";
import "package:flutter_test/flutter_test.dart";

import "package:expenis_mobile/service/base_service.dart";
import "package:expenis_mobile/service/personal_greeting_service.dart";

import "helpers/greeting_http.dart";

void main() {
  late GreetingHttp http;
  late PersonalGreetingService service;
  setUp(() {
    http = GreetingHttp();
    BaseService.debugSetDio(
      Dio(BaseOptions(validateStatus: (s) => s! < 500))
        ..httpClientAdapter = http,
    );
    service = PersonalGreetingService();
  });
  tearDown(BaseService.debugReset);

  test("parses empty result and Unicode text with UTC expiration", () async {
    expect(await service.fetchGreeting(), isNull);
    http.greeting = greetingJson(
      "Поздравляю 🎉\nHello",
      expiry: DateTime.utc(2030, 1, 1),
    );
    final greeting = (await service.fetchGreeting())!;
    expect(greeting.text, "Поздравляю 🎉\nHello");
    expect(greeting.expiresAt, DateTime.utc(2030, 1, 1));
    expect(greeting.expiresAt!.isUtc, isTrue);
    await service.dismissGreeting(greeting.id);
    expect(http.requests.last.path, endsWith("/assignment-A/dismiss"));
    expect(http.requests.last.method, "POST");
  });

  for (final status in [400, 403, 404, 500]) {
    test("reports HTTP $status for read and dismissal", () async {
      http.readStatus = status;
      http.dismissStatus = status;
      await expectLater(service.fetchGreeting(), throwsException);
      await expectLater(
        service.dismissGreeting("assignment-A"),
        throwsException,
      );
    });
  }
}
