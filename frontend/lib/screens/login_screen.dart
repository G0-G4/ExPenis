import "package:flutter/material.dart";

import "package:expenis_mobile/service/auth_service.dart";
import "package:expenis_mobile/service/settings_service.dart";
import "package:expenis_mobile/theme.dart";
import "package:expenis_mobile/widgets/app_loading_spinner.dart";

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final AuthService _authService = AuthService();
  final _formKey = GlobalKey<FormState>();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _obscurePassword = true;
  bool _isSubmitting = false;

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _isSubmitting = true);
    try {
      final session = await _authService.login(
        _usernameController.text.trim(),
        _passwordController.text,
      );
      final settingsService = await SettingsService.getInstance();
      await settingsService.setAccessToken(session.accessToken);
      await settingsService.setRefreshToken(session.refreshToken);
      await settingsService.setUsername(_usernameController.text.trim());
      if (!mounted) return;
      Navigator.of(context).pushReplacementNamed("/home");
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("$e")));
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Login")),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: AppTheme.screenPadding,
          children: [
            TextFormField(
              controller: _usernameController,
              decoration: const InputDecoration(
                labelText: "Username",
                prefixIcon: Icon(Icons.person_outline),
              ),
              textCapitalization: TextCapitalization.none,
              autofillHints: const [AutofillHints.username],
              validator: (value) => (value == null || value.trim().isEmpty)
                  ? "Please enter a username"
                  : null,
            ),
            const SizedBox(height: AppTheme.space16),
            TextFormField(
              controller: _passwordController,
              obscureText: _obscurePassword,
              decoration: InputDecoration(
                labelText: "Password",
                prefixIcon: const Icon(Icons.lock_outline),
                suffixIcon: IconButton(
                  icon: Icon(
                    _obscurePassword
                        ? Icons.visibility_outlined
                        : Icons.visibility_off_outlined,
                  ),
                  onPressed: () =>
                      setState(() => _obscurePassword = !_obscurePassword),
                ),
              ),
              autofillHints: const [AutofillHints.password],
              validator: (value) => (value == null || value.isEmpty)
                  ? "Please enter a password"
                  : null,
            ),
            const SizedBox(height: AppTheme.space32),
            FilledButton(
              onPressed: _isSubmitting ? null : _submit,
              child: _isSubmitting
                  ? const AppLoadingSpinner()
                  : const Text("Login"),
            ),
            const SizedBox(height: AppTheme.space16),
            TextButton(
              onPressed: _isSubmitting
                  ? null
                  : () => Navigator.of(context).pushNamed("/register"),
              child: const Text("Don't have an account? Register"),
            ),
          ],
        ),
      ),
    );
  }
}
