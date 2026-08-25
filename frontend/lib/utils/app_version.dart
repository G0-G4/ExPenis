import "dart:convert";

import "package:dio/dio.dart";
import "package:flutter/foundation.dart";
import "package:package_info_plus/package_info_plus.dart";

class AppVersion {
  const AppVersion({required this.version, required this.buildNumber});

  final String version;
  final String buildNumber;

  String get display => buildNumber.isEmpty ? version : "$version+$buildNumber";
}

AppVersion? parseVersionJson(Object? data) {
  Object? payload = data;
  if (payload is String && payload.isNotEmpty) {
    try {
      payload = jsonDecode(payload);
    } catch (_) {
      return null;
    }
  }
  if (payload is! Map) {
    return null;
  }
  final version = payload["version"];
  if (version is! String || version.isEmpty) {
    return null;
  }
  final build = payload["build_number"];
  return AppVersion(
    version: version,
    buildNumber: build is String ? build : "",
  );
}

/// Web reads `/version.json` directly. [PackageInfo.fromPlatform] uses a
/// MethodChannel fallback when the web plugin is not registered, which
/// throws MissingPluginException.
Future<AppVersion?> loadAppVersion() async {
  try {
    if (kIsWeb) {
      return await _loadFromVersionJson();
    }
    final info = await PackageInfo.fromPlatform();
    return AppVersion(version: info.version, buildNumber: info.buildNumber);
  } catch (_) {
    return null;
  }
}

Future<AppVersion?> _loadFromVersionJson() async {
  final url = Uri.parse(Uri.base.origin).replace(
    path: "/version.json",
    queryParameters: {
      "cachebuster": DateTime.now().millisecondsSinceEpoch.toString(),
    },
  );
  final response = await Dio(
    BaseOptions(
      validateStatus: (status) =>
          status != null && status >= 200 && status < 300,
    ),
  ).getUri(url);
  return parseVersionJson(response.data);
}
