import "dart:ui";
import "package:expenis_mobile/models/export.dart";

Future<ExportDeliveryResult> deliverExport(ExportFile file, {Rect? origin}) =>
    Future.error(
      UnsupportedError("Сохранение файла недоступно на этой платформе"),
    );

Future<void> cleanupExportFiles() async {}
