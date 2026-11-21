import "dart:io";
import "dart:ui";

import "package:flutter/foundation.dart";
import "package:flutter_test/flutter_test.dart";
import "package:share_plus/share_plus.dart";

import "package:expenis_mobile/models/export.dart";
import "package:expenis_mobile/service/export_delivery_io.dart";

void main() {
  late Directory root;
  final file = ExportFile(
    bytes: Uint8List.fromList([1, 2, 3]),
    name: "history.csv",
    mimeType: "text/csv",
  );
  setUp(
    () async => root = await Directory.systemTemp.createTemp("export-test-"),
  );
  tearDown(() async {
    await root.delete(recursive: true);
  });

  test("desktop writes actual bytes to selected location", () async {
    final target = "${root.path}/history.csv";
    final delivery = NativeExportDelivery(
      platform: TargetPlatform.linux,
      choosePath: (name) async {
        expect(name, file.name);
        return target;
      },
    );
    expect(await delivery.deliver(file), ExportDeliveryResult.saved);
    expect(await File(target).readAsBytes(), file.bytes);
  });
  test("desktop cancellation writes nothing", () async {
    final delivery = NativeExportDelivery(
      platform: TargetPlatform.macOS,
      choosePath: (_) async => null,
    );
    expect(await delivery.deliver(file), ExportDeliveryResult.cancelled);
    expect(root.listSync(), isEmpty);
  });
  test("write failures propagate", () async {
    final delivery = NativeExportDelivery(
      platform: TargetPlatform.windows,
      choosePath: (_) async => "${root.path}/missing/history.csv",
    );
    await expectLater(
      delivery.deliver(file),
      throwsA(isA<FileSystemException>()),
    );
  });
  test("mobile passes file bytes MIME and iPad anchor to share", () async {
    const anchor = Rect.fromLTWH(10, 20, 100, 50);
    final stale = await root.createTemp("expenis-export-");
    // The cleanup policy retains files handed off less than one day ago.
    final delivery = NativeExportDelivery(
      platform: TargetPlatform.iOS,
      temporaryDirectory: () async => root,
      share: (params) async {
        expect(params.sharePositionOrigin, anchor);
        expect(params.files!.single.mimeType, file.mimeType);
        expect(await params.files!.single.readAsBytes(), file.bytes);
        expect(params.files!.single.path.endsWith(file.name), isTrue);
        return const ShareResult("", ShareResultStatus.success);
      },
    );
    expect(
      await delivery.deliver(file, origin: anchor),
      ExportDeliveryResult.handedOff,
    );
    expect(await stale.exists(), isTrue);
    expect(root.listSync().length, 2);
  });
  test("mobile cancellation cleans temporary file", () async {
    final delivery = NativeExportDelivery(
      platform: TargetPlatform.android,
      temporaryDirectory: () async => root,
      share: (_) async => const ShareResult("", ShareResultStatus.dismissed),
    );
    expect(await delivery.deliver(file), ExportDeliveryResult.cancelled);
    expect(root.listSync(), isEmpty);
  });
  test(
    "startup cleanup removes expired exports and preserves unrelated files",
    () async {
      final stale = await root.createTemp("expenis-export-");
      await File("${stale.path}/history.csv").writeAsBytes(file.bytes);
      final unrelated = await root.createTemp("other-");
      await NativeExportDelivery(
        temporaryDirectory: () async => root,
        now: () => DateTime.now().add(const Duration(days: 2)),
      ).cleanup();
      expect(await stale.exists(), isFalse);
      expect(await unrelated.exists(), isTrue);
    },
  );
  test("share error cleans temporary file", () async {
    final delivery = NativeExportDelivery(
      platform: TargetPlatform.android,
      temporaryDirectory: () async => root,
      share: (_) async => throw Exception("share failed"),
    );
    await expectLater(delivery.deliver(file), throwsException);
    expect(root.listSync(), isEmpty);
  });
}
