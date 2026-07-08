import "package:flutter/material.dart";
import "package:package_info_plus/package_info_plus.dart";

import "package:expenis_mobile/service/auth_service.dart";
import "package:expenis_mobile/service/settings_service.dart";
import "package:expenis_mobile/widgets/app_loading_spinner.dart";
import "package:expenis_mobile/theme.dart";

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final AuthService _authService = AuthService();
  UserProfile? _profile;
  String? _appVersion;
  bool _isLoading = false;
  bool _isLoggingOut = false;
  String? _loadError;

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  Future<void> _loadProfile() async {
    if (!mounted) return;
    setState(() {
      _isLoading = true;
      _loadError = null;
    });
    try {
      final settingsService = await SettingsService.getInstance();
      final accessToken = await settingsService.getAccessToken();
      if (accessToken == null || accessToken.isEmpty) {
        throw Exception("Not authenticated");
      }
      final profile = await _authService.me(accessToken);
      final info = await PackageInfo.fromPlatform();
      if (!mounted) return;
      setState(() {
        _profile = profile;
        _appVersion = "${info.version}+${info.buildNumber}";
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loadError = "$e";
        _isLoading = false;
      });
    }
  }

  Future<void> _logout() async {
    if (!mounted) return;
    setState(() => _isLoggingOut = true);
    try {
      final settingsService = await SettingsService.getInstance();
      final accessToken = await settingsService.getAccessToken();
      if (accessToken != null && accessToken.isNotEmpty) {
        try {
          await _authService.logout(accessToken);
        } catch (_) {
          // Even if the server call fails, clear local state.
        }
      }
      await settingsService.clearAuth();
      if (!mounted) return;
      Navigator.of(context).pushNamedAndRemoveUntil("/login", (_) => false);
    } finally {
      if (mounted) setState(() => _isLoggingOut = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final colorScheme = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(title: const Text("Settings")),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _loadProfile,
              child: ListView(
                padding: AppTheme.screenPadding,
                children: [
                  Text(
                    "Account",
                    style: textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: AppTheme.space8),
                  Text(
                    "Manage your account and security settings",
                    style: textTheme.bodyMedium?.copyWith(
                      color: colorScheme.onSurfaceVariant,
                    ),
                  ),
                  const SizedBox(height: AppTheme.space24),
                  Card(
                    child: Padding(
                      padding: AppTheme.cardPadding,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          _ProfileRow(
                            icon: Icons.person_outline,
                            label: "Username",
                            value: _profile?.username ?? "—",
                          ),
                          if (_profile?.telegramId != null) ...[
                            const SizedBox(height: AppTheme.space12),
                            Divider(color: colorScheme.outlineVariant),
                            const SizedBox(height: AppTheme.space12),
                            _ProfileRow(
                              icon: Icons.tag_rounded,
                              label: "Telegram ID",
                              value: "${_profile!.telegramId}",
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                  if (_loadError != null) ...[
                    const SizedBox(height: AppTheme.space12),
                    Text(
                      "Failed to load profile: $_loadError",
                      style: TextStyle(color: colorScheme.error),
                    ),
                  ],
                  const SizedBox(height: AppTheme.space24),
                  ListTile(
                    leading: const Icon(Icons.lock_outline),
                    title: const Text("Change password"),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () =>
                        Navigator.of(context).pushNamed("/change-password"),
                  ),
                  const SizedBox(height: AppTheme.space16),
                  FilledButton.icon(
                    onPressed: _isLoggingOut ? null : _logout,
                    icon: _isLoggingOut
                        ? const AppLoadingSpinner()
                        : const Icon(
                            Icons.logout,
                            size: AppTheme.iconSizeMedium,
                          ),
                    label: const Text("Log out"),
                    style: FilledButton.styleFrom(
                      backgroundColor: colorScheme.errorContainer,
                      foregroundColor: colorScheme.onErrorContainer,
                    ),
                  ),
                  const SizedBox(height: AppTheme.space32),
                  Text(
                    "About",
                    style: textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: AppTheme.space16),
                  Card(
                    child: Padding(
                      padding: AppTheme.cardPadding,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          _InfoRow(
                            icon: Icons.cloud_outlined,
                            label: "Server",
                            value: "expenis.g0g4.ru",
                          ),
                          const SizedBox(height: AppTheme.space12),
                          Divider(color: colorScheme.outlineVariant),
                          const SizedBox(height: AppTheme.space12),
                          _InfoRow(
                            icon: Icons.info_outline,
                            label: "Version",
                            value: _appVersion ?? "—",
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
    );
  }
}

class _ProfileRow extends StatelessWidget {
  const _ProfileRow({
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final colorScheme = Theme.of(context).colorScheme;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(
          icon,
          size: AppTheme.iconSizeMedium,
          color: colorScheme.onSurfaceVariant,
        ),
        const SizedBox(width: AppTheme.space12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: textTheme.labelMedium?.copyWith(
                  color: colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: AppTheme.space2),
              Text(value, style: textTheme.bodyMedium),
            ],
          ),
        ),
      ],
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final colorScheme = Theme.of(context).colorScheme;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(
          icon,
          size: AppTheme.iconSizeMedium,
          color: colorScheme.onSurfaceVariant,
        ),
        const SizedBox(width: AppTheme.space12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: textTheme.labelMedium?.copyWith(
                  color: colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: AppTheme.space2),
              Text(value, style: textTheme.bodyMedium),
            ],
          ),
        ),
      ],
    );
  }
}
