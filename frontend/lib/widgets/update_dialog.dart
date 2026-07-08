import "package:flutter/material.dart";
import "package:url_launcher/url_launcher.dart";

import "package:expenis_mobile/service/update_service.dart";
import "package:expenis_mobile/theme.dart";

Future<void> showUpdateDialog(BuildContext context, UpdateInfo updateInfo) {
  return showDialog<void>(
    context: context,
    barrierDismissible: false,
    builder: (_) => UpdateDialog(updateInfo: updateInfo),
  );
}

class UpdateDialog extends StatefulWidget {
  const UpdateDialog({super.key, required this.updateInfo});

  final UpdateInfo updateInfo;

  @override
  State<UpdateDialog> createState() => _UpdateDialogState();
}

class _UpdateDialogState extends State<UpdateDialog> {
  final UpdateService _service = UpdateService();
  bool _downloading = false;
  double _progress = 0;
  String? _error;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final info = widget.updateInfo;

    return AlertDialog(
      title: Row(
        children: [
          Icon(Icons.system_update, color: colorScheme.primary),
          const SizedBox(width: AppTheme.space12),
          const Expanded(child: Text("Update available")),
        ],
      ),
      content: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 360),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                "Version ${info.latestVersion} "
                "(current ${info.currentVersion})",
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: AppTheme.space12),
              if (info.releaseNotes.isNotEmpty) ...[
                Text(
                  "Release notes",
                  style: Theme.of(context).textTheme.labelLarge,
                ),
                const SizedBox(height: AppTheme.space4),
                Text(
                  info.releaseNotes,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
              if (_downloading) ...[
                const SizedBox(height: AppTheme.space16),
                LinearProgressIndicator(value: _progress),
                const SizedBox(height: AppTheme.space4),
                Text(
                  "${(_progress * 100).round()}%",
                  style: Theme.of(context).textTheme.labelSmall,
                ),
              ],
              if (_error != null) ...[
                const SizedBox(height: AppTheme.space12),
                Text(_error!, style: TextStyle(color: colorScheme.error)),
              ],
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: _downloading ? null : () => Navigator.of(context).pop(),
          child: const Text("Later"),
        ),
        FilledButton.icon(
          onPressed: _downloading
              ? null
              : (info.canInstallApk ? _onUpdateTap : _openReleasePage),
          icon: _downloading
              ? const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : Icon(
                  info.canInstallApk
                      ? Icons.download_rounded
                      : Icons.open_in_new,
                ),
          label: Text(info.canInstallApk ? "Update" : "Open"),
        ),
      ],
    );
  }

  Future<void> _onUpdateTap() async {
    if (!mounted) return;
    setState(() {
      _downloading = true;
      _error = null;
      _progress = 0;
    });

    try {
      final url = widget.updateInfo.downloadUrl!;
      final file = await _service.downloadApk(
        url,
        onProgress: (received, total) {
          if (total <= 0) return;
          if (!mounted) return;
          setState(() => _progress = received / total);
        },
      );
      if (!mounted) return;
      await _service.installApk(file.path);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = "Failed to download update: $e";
        _downloading = false;
      });
    }
  }

  Future<void> _openReleasePage() async {
    final uri = Uri.parse(widget.updateInfo.htmlUrl);
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }
}
