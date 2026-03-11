import 'package:flutter/material.dart';

import 'package:expenis_mobile/service/settings_service.dart';
import 'package:expenis_mobile/theme.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final TextEditingController _apiKeyController = TextEditingController();
  bool _isLoading = false;
  bool _obscureText = true;

  @override
  void initState() {
    super.initState();
    _loadApiKey();
  }

  Future<void> _loadApiKey() async {
    if (!mounted) return;
    setState(() => _isLoading = true);
    try {
      final settingsService = await SettingsService.getInstance();
      final apiKey = await settingsService.getApiKey();
      if (!mounted) return;
      if (apiKey != null) {
        _apiKeyController.text = apiKey;
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Error loading API key: $e')));
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _saveApiKey() async {
    if (!mounted) return;
    setState(() => _isLoading = true);
    try {
      final settingsService = await SettingsService.getInstance();
      await settingsService.setApiKey(_apiKeyController.text.trim());
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('API key saved successfully')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Error saving API key: $e')));
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _clearApiKey() async {
    if (!mounted) return;
    setState(() => _isLoading = true);
    try {
      final settingsService = await SettingsService.getInstance();
      await settingsService.clearApiKey();
      if (!mounted) return;
      _apiKeyController.clear();
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('API key cleared')));
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Error clearing API key: $e')));
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  void dispose() {
    _apiKeyController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final colorScheme = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: AppTheme.screenPadding,
              children: [
                // ── API Configuration section ─────────────────────────
                Text(
                  'API Configuration',
                  style: textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: AppTheme.space8),
                Text(
                  'Configure your server connection',
                  style: textTheme.bodyMedium?.copyWith(
                    color: colorScheme.onSurfaceVariant,
                  ),
                ),
                const SizedBox(height: AppTheme.space24),

                // API Key field
                TextFormField(
                  controller: _apiKeyController,
                  obscureText: _obscureText,
                  decoration: InputDecoration(
                    labelText: 'API Key',
                    hintText: 'Enter your API key',
                    prefixIcon: const Icon(Icons.key_outlined),
                    suffixIcon: IconButton(
                      icon: Icon(
                        _obscureText
                            ? Icons.visibility_outlined
                            : Icons.visibility_off_outlined,
                      ),
                      onPressed: () =>
                          setState(() => _obscureText = !_obscureText),
                    ),
                  ),
                ),
                const SizedBox(height: AppTheme.space16),

                // Action buttons
                Row(
                  children: [
                    Expanded(
                      child: FilledButton.icon(
                        onPressed: _saveApiKey,
                        icon: const Icon(
                          Icons.save_outlined,
                          size: AppTheme.iconSizeMedium,
                        ),
                        label: const Text('Save'),
                      ),
                    ),
                    const SizedBox(width: AppTheme.space12),
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: _clearApiKey,
                        icon: const Icon(
                          Icons.delete_outline,
                          size: AppTheme.iconSizeMedium,
                        ),
                        label: const Text('Clear'),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: AppTheme.space32),

                // ── About section ─────────────────────────────────────
                Text(
                  'About',
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
                          icon: Icons.info_outline_rounded,
                          label: 'API Key',
                          value:
                              'Included in all requests to the backend server. '
                              'Enter a valid key provided by your administrator.',
                        ),
                        const SizedBox(height: AppTheme.space12),
                        Divider(color: colorScheme.outlineVariant),
                        const SizedBox(height: AppTheme.space12),
                        _InfoRow(
                          icon: Icons.cloud_outlined,
                          label: 'Server',
                          value: 'expenis.g0g4.ru',
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
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
