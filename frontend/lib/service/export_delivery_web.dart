import "dart:js_interop";
import "dart:ui";

import "package:web/web.dart" as web;

import "package:expenis_mobile/models/export.dart";

Future<ExportDeliveryResult> deliverExport(
  ExportFile file, {
  Rect? origin,
}) async {
  final blob = web.Blob(
    [file.bytes.toJS].toJS,
    web.BlobPropertyBag(type: file.mimeType),
  );
  final url = web.URL.createObjectURL(blob);
  final anchor = web.HTMLAnchorElement()
    ..href = url
    ..download = file.name;
  try {
    web.document.body!.appendChild(anchor);
    anchor.click();
    // Let the browser consume the object URL before releasing its backing bytes.
    await Future<void>.delayed(const Duration(seconds: 1));
    return ExportDeliveryResult.handedOff;
  } finally {
    anchor.remove();
    web.URL.revokeObjectURL(url);
  }
}

Future<void> cleanupExportFiles() async {}
