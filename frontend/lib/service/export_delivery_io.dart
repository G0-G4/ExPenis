import "dart:io";
import "dart:ui";

import "package:file_selector/file_selector.dart";
import "package:flutter/foundation.dart";
import "package:path_provider/path_provider.dart";
import "package:share_plus/share_plus.dart";

import "package:expenis_mobile/models/export.dart";

Future<ExportDeliveryResult> deliverExport(ExportFile file, {Rect? origin}) =>
    NativeExportDelivery().deliver(file, origin: origin);

Future<void> cleanupExportFiles() => NativeExportDelivery().cleanup();

class NativeExportDelivery {
  NativeExportDelivery({
    TargetPlatform? platform,
    Future<Directory> Function()? temporaryDirectory,
    DateTime Function()? now,
    Future<String?> Function(String name)? choosePath,
    Future<ShareResult> Function(ShareParams params)? share,
  }) : _platform = platform ?? defaultTargetPlatform,
       _temporaryDirectory = temporaryDirectory ?? getTemporaryDirectory,
       _now = now ?? DateTime.now,
       _choosePath = choosePath ?? _savePath,
       _share = share ?? SharePlus.instance.share;

  final TargetPlatform _platform;
  final Future<Directory> Function() _temporaryDirectory;
  final DateTime Function() _now;
  final Future<String?> Function(String name) _choosePath;
  final Future<ShareResult> Function(ShareParams params) _share;

  static Future<String?> _savePath(String name) async =>
      (await getSaveLocation(suggestedName: name))?.path;

  Future<void> cleanup() async => _cleanup(await _temporaryDirectory());

  Future<void> _cleanup(Directory root) async {
    // Retain handed-off files briefly: a receiving app can read after the share sheet closes.
    await for (final entity in root.list()) {
      if (entity is Directory &&
          entity.path
              .split(Platform.pathSeparator)
              .last
              .startsWith("expenis-export-") &&
          _now().difference((await entity.stat()).modified) >
              const Duration(days: 1)) {
        await entity.delete(recursive: true);
      }
    }
  }

  Future<ExportDeliveryResult> deliver(ExportFile file, {Rect? origin}) async {
    if (_platform != TargetPlatform.android &&
        _platform != TargetPlatform.iOS) {
      final path = await _choosePath(file.name);
      if (path == null) return ExportDeliveryResult.cancelled;
      await XFile.fromData(
        file.bytes,
        mimeType: file.mimeType,
        name: file.name,
      ).saveTo(path);
      return ExportDeliveryResult.saved;
    }
    final root = await _temporaryDirectory();
    await _cleanup(root);
    final directory = await root.createTemp("expenis-export-");
    final path = "${directory.path}${Platform.pathSeparator}${file.name}";
    try {
      await File(path).writeAsBytes(file.bytes, flush: true);
      final result = await _share(
        ShareParams(
          files: [XFile(path, mimeType: file.mimeType)],
          sharePositionOrigin: origin,
          title: "Экспорт операций",
        ),
      );
      if (result.status == ShareResultStatus.dismissed) {
        await directory.delete(recursive: true);
        return ExportDeliveryResult.cancelled;
      }
      return ExportDeliveryResult.handedOff;
    } catch (_) {
      if (await directory.exists()) await directory.delete(recursive: true);
      rethrow;
    }
  }
}
