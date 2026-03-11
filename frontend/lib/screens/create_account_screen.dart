import 'package:flutter/material.dart';
import 'package:flutter_typeahead/flutter_typeahead.dart';

import 'package:expenis_mobile/service/account_service.dart';
import 'package:expenis_mobile/theme.dart';
import 'package:expenis_mobile/widgets/app_loading_spinner.dart';

class CreateAccountScreen extends StatefulWidget {
  const CreateAccountScreen({super.key});

  @override
  State<CreateAccountScreen> createState() => _CreateAccountScreenState();
}

class _CreateAccountScreenState extends State<CreateAccountScreen> {
  final AccountService _accountService = AccountService();
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _amountController = TextEditingController();
  final _currencyController = TextEditingController();
  late Future<List<String>> _futureCurrencyCodes;
  bool _isSaving = false;

  @override
  void initState() {
    super.initState();
    _futureCurrencyCodes = _accountService.fetchCurrencyCodes();
  }

  Future<void> _createAccount() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _isSaving = true);
    try {
      final newAccount = await _accountService.createAccount(
        _nameController.text.trim(),
        double.parse(_amountController.text),
        _currencyController.text.trim(),
      );
      if (!mounted) return;
      Navigator.pop(context, newAccount);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Failed to create account: $e')));
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  @override
  void dispose() {
    _nameController.dispose();
    _amountController.dispose();
    _currencyController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('New Account')),
      body: Form(
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
              decoration: const InputDecoration(
                labelText: 'Initial Balance',
                prefixIcon: Icon(Icons.currency_ruble),
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
            FutureBuilder<List<String>>(
              future: _futureCurrencyCodes,
              builder: (context, snapshot) {
                if (snapshot.hasData) {
                  return TypeAheadField<String>(
                    controller: _currencyController,
                    builder: (context, controller, focusNode) {
                      return TextFormField(
                        controller: controller,
                        focusNode: focusNode,
                        decoration: const InputDecoration(
                          labelText: 'Currency Code',
                          prefixIcon: Icon(Icons.language_outlined),
                          hintText: 'e.g. RUB, USD',
                        ),
                        validator: (value) => (value == null || value.isEmpty)
                            ? 'Please select a currency'
                            : null,
                      );
                    },
                    suggestionsCallback: (pattern) => snapshot.data!
                        .where(
                          (code) => code.toLowerCase().contains(
                            pattern.toLowerCase(),
                          ),
                        )
                        .toList(),
                    itemBuilder: (context, suggestion) =>
                        ListTile(title: Text(suggestion)),
                    onSelected: (suggestion) {
                      setState(() {
                        _currencyController.text = suggestion;
                      });
                    },
                  );
                } else if (snapshot.hasError) {
                  return Text(
                    'Failed to load currencies',
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.error,
                    ),
                  );
                }
                return const Center(child: CircularProgressIndicator());
              },
            ),
            const SizedBox(height: AppTheme.space32),
            FilledButton(
              onPressed: _isSaving ? null : _createAccount,
              child: _isSaving
                  ? const AppLoadingSpinner()
                  : const Text('Create Account'),
            ),
          ],
        ),
      ),
    );
  }
}
