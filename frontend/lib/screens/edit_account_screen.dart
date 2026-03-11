import 'package:flutter/material.dart';

import 'package:expenis_mobile/models/account.dart';
import 'package:expenis_mobile/service/account_service.dart';
import 'package:expenis_mobile/theme.dart';
import 'package:expenis_mobile/widgets/app_error_state.dart';
import 'package:expenis_mobile/widgets/app_loading_spinner.dart';
import 'package:expenis_mobile/widgets/delete_dialog.dart';

class EditAccountScreen extends StatefulWidget {
  final int accountId;

  const EditAccountScreen({super.key, required this.accountId});

  @override
  State<EditAccountScreen> createState() => _EditAccountScreenState();
}

class _EditAccountScreenState extends State<EditAccountScreen> {
  final AccountService _accountService = AccountService();
  final _formKey = GlobalKey<FormState>();

  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _amountController = TextEditingController();

  bool _isLoading = true;
  bool _isSaving = false;
  String? _error;
  Account? _account;

  @override
  void initState() {
    super.initState();
    _fetchAccount();
  }

  Future<void> _fetchAccount() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final account = await _accountService.fetchAccount(widget.accountId);
      if (!mounted) return;
      setState(() {
        _account = account;
        _nameController.text = account.name;
        _amountController.text = account.amount.toString();
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  Future<void> _updateAccount() async {
    if (_account == null || !_formKey.currentState!.validate()) return;
    setState(() => _isSaving = true);
    try {
      final updated = _account!.copyWith(
        name: _nameController.text.trim(),
        amount: double.parse(_amountController.text),
      );
      await _accountService.updateAccount(updated);
      if (!mounted) return;
      Navigator.pop(context, true);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Failed to update account: $e')));
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  Future<void> _deleteAccount() async {
    final confirmed = await showDeleteDialog(
      context: context,
      resourceName: 'account',
    );
    if (!confirmed || !mounted) return;
    try {
      await _accountService.deleteAccount(widget.accountId);
      if (!mounted) return;
      Navigator.pop(context, true);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Failed to delete account: $e')));
    }
  }

  @override
  void dispose() {
    _nameController.dispose();
    _amountController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Edit Account'),
        actions: [
          if (!_isLoading && _error == null)
            IconButton(
              icon: Icon(
                Icons.delete_outline,
                color: Theme.of(context).colorScheme.error,
              ),
              tooltip: 'Delete',
              onPressed: _deleteAccount,
            ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
          ? AppErrorState(message: _error!, onRetry: _fetchAccount)
          : Form(
              key: _formKey,
              child: ListView(
                padding: AppTheme.screenPadding,
                children: [
                  TextFormField(
                    controller: _nameController,
                    decoration: const InputDecoration(
                      labelText: 'Account Name',
                      prefixIcon: Icon(Icons.account_balance_outlined),
                    ),
                    textCapitalization: TextCapitalization.words,
                    validator: (value) => (value == null || value.isEmpty)
                        ? 'Please enter a name'
                        : null,
                  ),
                  const SizedBox(height: AppTheme.space16),
                  TextFormField(
                    controller: _amountController,
                    decoration: InputDecoration(
                      labelText: 'Balance',
                      prefixIcon: const Icon(Icons.attach_money_outlined),
                      suffixText: _account?.currencyCode,
                    ),
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                    ),
                    validator: (value) {
                      if (value == null || value.isEmpty) {
                        return 'Please enter an amount';
                      }
                      if (double.tryParse(value) == null) {
                        return 'Please enter a valid number';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: AppTheme.space16),
                  TextFormField(
                    initialValue: _account!.currencyCode,
                    enabled: false,
                    decoration: const InputDecoration(
                      labelText: 'Currency Code',
                      prefixIcon: Icon(Icons.language_outlined),
                    ),
                  ),
                  const SizedBox(height: AppTheme.space32),
                  FilledButton(
                    onPressed: _isSaving ? null : _updateAccount,
                    child: _isSaving
                        ? const AppLoadingSpinner()
                        : const Text('Save Changes'),
                  ),
                ],
              ),
            ),
    );
  }
}
