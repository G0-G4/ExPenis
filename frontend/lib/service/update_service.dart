import "dart:io";

import "package:dio/dio.dart";
import "package:flutter/foundation.dart";
import "package:flutter/services.dart";
import "package:package_info_plus/package_info_plus.dart";
import "package:path_provider/path_provider.dart";

const String _githubOwner = "G0-G4";
const String _githubRepo = "ExPenis";
const String _githubApiLatest =
    "https://api.github.com/repos/$_githubOwner/$_githubRepo/releases/latest";

const String _installerChannel = "expenis/installer";

class UpdateInfo {
  const UpdateInfo({
    required this.currentVersion,
    required this.latestVersion,
    required this.releaseNotes,
    required this.htmlUrl,
    this.downloadUrl,
  });

  final String currentVersion;
  final String latestVersion;
  final String releaseNotes;
  final String htmlUrl;
  final String? downloadUrl;

  bool get hasUpdate =>
      UpdateService.compareSemver(latestVersion, currentVersion) > 0;

  bool get canInstallApk =>
      defaultTargetPlatform == TargetPlatform.android && downloadUrl != null;
}

class UpdateService {
  UpdateService._();

  static final UpdateService _instance = UpdateService._();
  factory UpdateService() => _instance;

  final Dio _dio = Dio(
    BaseOptions(
      headers: {"Accept": "application/vnd.github+json"},
      validateStatus: (status) =>
          status != null && status >= 200 && status < 300,
    ),
  );

  Future<UpdateInfo?> checkForUpdate() async {
    try {
      final info = await PackageInfo.fromPlatform();
      final current = info.version;

      final response = await _dio.get<dynamic>(_githubApiLatest);
      final data = response.data as Map<String, dynamic>;

      final tagName = data["tag_name"] as String? ?? "";
      final latest = tagName.startsWith("v") ? tagName.substring(1) : tagName;

      final htmlUrl = data["html_url"] as String? ?? "";
      final releaseNotes = data["body"] as String? ?? "";

      String? downloadUrl;
      final assets = data["assets"] as List<dynamic>?;
      if (assets != null) {
        for (final asset in assets) {
          final name = asset["name"] as String? ?? "";
          if (name.endsWith(".apk")) {
            downloadUrl = asset["browser_download_url"] as String?;
            break;
          }
        }
      }

      return UpdateInfo(
        currentVersion: current,
        latestVersion: latest,
        releaseNotes: releaseNotes,
        htmlUrl: htmlUrl,
        downloadUrl: downloadUrl,
      );
    } on DioException catch (_) {
      return null;
    } catch (_) {
      return null;
    }
  }

  Future<File> downloadApk(
    String downloadUrl, {
    void Function(int received, int total)? onProgress,
    CancelToken? cancelToken,
  }) async {
    final dir = await getTemporaryDirectory();
    final filePath = "${dir.path}/ExPenis-latest.apk";
    if (File(filePath).existsSync()) {
      File(filePath).deleteSync();
    }
    await _dio.download(
      downloadUrl,
      filePath,
      onReceiveProgress: onProgress,
      cancelToken: cancelToken,
    );
    return File(filePath);
  }

  Future<void> installApk(String filePath) async {
    if (defaultTargetPlatform != TargetPlatform.android) {
      throw UnsupportedError("APK install is supported only on Android");
    }
    final channel = const MethodChannel(_installerChannel);
    await channel.invokeMethod<bool>("installApk", {"path": filePath});
  }

  /// Returns positive if [a] > [b], negative if [a] < [b], zero if equal.
  static int compareSemver(String a, String b) {
    final partsA = _parseSemver(a);
    final partsB = _parseSemver(b);
    for (var i = 0; i < 3; i++) {
      final cmp = partsA[i].compareTo(partsB[i]);
      if (cmp != 0) return cmp;
    }
    return 0;
  }

  static List<int> _parseSemver(String version) {
    final clean = version.split("+").first.split("-").first;
    final parts = clean.split(".");
    final major = int.tryParse(parts.isNotEmpty ? parts[0] : "") ?? 0;
    final minor = int.tryParse(parts.length > 1 ? parts[1] : "") ?? 0;
    final patch = int.tryParse(parts.length > 2 ? parts[2] : "") ?? 0;
    return [major, minor, patch];
  }
}
