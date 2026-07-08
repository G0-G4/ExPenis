import "package:flutter/material.dart";

import "package:expenis_mobile/service/auth_service.dart";
import "package:expenis_mobile/service/settings_service.dart";
import "package:expenis_mobile/theme.dart";
import "package:expenis_mobile/widgets/app_loading_spinner.dart";

class ChangePasswordScreen extends StatefulWidget {
  const ChangePasswordScreen({super.key});

  @override
  State<ChangePasswordScreen> createState() => _ChangePasswordScreenState();
}

class _ChangePasswordScreenState extends State<ChangePasswordScreen> {
  final AuthService _authService = AuthService();
  final _formKey = GlobalKey<FormState>();
  final _oldController = TextEditingController();
  final _newController = TextEditingController();
  final _confirmController = TextEditingController();
  bool _obscureOld = true;
  bool _obscureNew = true;
  bool _obscureConfirm = true;
  bool _isSubmitting = false;

  @override
  void dispose() {
    _oldController.dispose();
    _newController.dispose();
    _confirmController.dispose();
    super.dispose();
  }

  String? _validateNewPassword(String? value) {
    if (value == null || value.isEmpty) {
      return "Please enter a new password";
    }
    if (value.length < 6) {
      return "Password must be at least 6 characters";
    }
    return null;
  }

  String? _validateConfirm(String? value) {
    if (value == null || value.isEmpty) {
      return "Please confirm your new password";
    }
    if (value != _newController.text) {
      return "Passwords do not match";
    }
    return null;
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _isSubmitting = true);
    try {
      final settingsService = await SettingsService.getInstance();
      final accessToken = await settingsService.getAccessToken();
      if (accessToken == null || accessToken.isEmpty) {
        throw Exception("Not authenticated");
      }
      await _authService.changePassword(
        accessToken,
        oldPassword: _oldController.text,
        newPassword: _newController.text,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Password changed successfully")),
      );
      Navigator.of(context).pop();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("$e")));
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  Widget _buildField({
    required TextEditingController controller,
    required String label,
    required bool obscure,
    required VoidCallback onToggle,
    required String? Function(String?) validator,
  }) {
    return TextFormField(
      controller: controller,
      obscureText: obscure,
      decoration: InputDecoration(
        labelText: label,
        prefixIcon: const Icon(Icons.lock_outline),
        suffixIcon: IconButton(
          icon: Icon(
            obscure ? Icons.visibility_outlined : Icons.visibility_off_outlined,
          ),
          onPressed: onToggle,
        ),
      ),
      validator: validator,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Change Password")),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: AppTheme.screenPadding,
          children: [
            _buildField(
              controller: _oldController,
              label: "Current Password",
              obscure: _obscureOld,
              onToggle: () => setState(() => _obscureOld = !_obscureOld),
              validator: (value) => (value == null || value.isEmpty)
                  ? "Please enter your current password"
                  : null,
            ),
            const SizedBox(height: AppTheme.space16),
            _buildField(
              controller: _newController,
              label: "New Password",
              obscure: _obscureNew,
              onToggle: () => setState(() => _obscureNew = !_obscureNew),
              validator: _validateNewPassword,
            ),
            const SizedBox(height: AppTheme.space16),
            _buildField(
              controller: _confirmController,
              label: "Confirm New Password",
              obscure: _obscureConfirm,
              onToggle: () =>
                  setState(() => _obscureConfirm = !_obscureConfirm),
              validator: _validateConfirm,
            ),
            const SizedBox(height: AppTheme.space32),
            FilledButton(
              onPressed: _isSubmitting ? null : _submit,
              child: _isSubmitting
                  ? const AppLoadingSpinner()
                  : const Text("Change Password"),
            ),
          ],
        ),
      ),
    );
  }
}
