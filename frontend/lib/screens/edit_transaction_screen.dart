import 'package:flutter/material.dart';
import 'package:flutter_typeahead/flutter_typeahead.dart';

import 'package:expenis_mobile/models/account.dart';
import 'package:expenis_mobile/models/category.dart';
import 'package:expenis_mobile/models/transaction.dart';
import 'package:expenis_mobile/service/account_service.dart'
    show AccountService, AccountsResult;
import 'package:expenis_mobile/service/category_service.dart';
import 'package:expenis_mobile/service/transaction_service.dart';
import 'package:expenis_mobile/theme.dart';
import 'package:expenis_mobile/widgets/app_loading_spinner.dart';
import 'package:expenis_mobile/widgets/delete_dialog.dart';

class EditTransactionScreen extends StatefulWidget {
  final int? transactionId;
  final DateTime? initialDate;

  const EditTransactionScreen({
    super.key,
    this.transactionId,
    this.initialDate,
  });

  @override
  State<EditTransactionScreen> createState() => _EditTransactionScreenState();
}

class _EditTransactionScreenState extends State<EditTransactionScreen> {
  final TransactionService _transactionService = TransactionService();
  final AccountService _accountService = AccountService();
  final CategoryService _categoryService = CategoryService();
  final _formKey = GlobalKey<FormState>();
  late Future<AccountsResult> _futureAccounts;
  late Future<List<Category>> _futureCategories;

  final TextEditingController _descriptionController = TextEditingController();
  final TextEditingController _amountController = TextEditingController();
  final TextEditingController _tagController = TextEditingController();
  late DateTime _selectedDate;
  CategoryType _transactionType = CategoryType.expense;
  int? _selectedAccountId;
  int? _selectedCategoryId;
  List<String> _allTags = [];
  List<String> _selectedTags = [];
  bool _isSaving = false;

  bool get _isEditing => widget.transactionId != null;

  // Accounts are loaded into this list so we can look up currency codes.
  List<Account> _accounts = [];

  String get _selectedCurrencyCode {
    if (_selectedAccountId == null) return '';
    final match = _accounts.where((a) => a.id == _selectedAccountId);
    return match.isNotEmpty ? match.first.currencyCode : '';
  }

  @override
  void initState() {
    super.initState();
    _selectedDate = _initialDateForCreate(widget.initialDate ?? DateTime.now());
    _futureAccounts = _accountService.fetchAccounts();
    _futureCategories = _categoryService.fetchCategories();
    _loadTags();

    if (_isEditing) {
      _transactionService.fetchTransaction(widget.transactionId!).then((
        transaction,
      ) {
        if (!mounted) return;
        setState(() {
          _descriptionController.text = transaction.description ?? '';
          _amountController.text = transaction.amount.toString();
          _transactionType = transaction.type == TransactionType.income
              ? CategoryType.income
              : CategoryType.expense;
          _selectedAccountId = transaction.accountId;
          _selectedCategoryId = transaction.categoryId;
          _selectedDate = transaction.createdAt ?? _selectedDate;
          _selectedTags = List<String>.from(transaction.tags);
        });
      });
    }
  }

  Future<void> _loadTags() async {
    try {
      final tags = await _transactionService.fetchTags();
      if (!mounted) return;
      setState(() {
        _allTags = tags;
      });
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Failed to load tags')));
    }
  }

  String _normalizeTag(String tag) => tag.trim().toLowerCase();

  bool _isTagSelected(String tag) {
    final normalized = _normalizeTag(tag);
    return _selectedTags.any(
      (selected) => _normalizeTag(selected) == normalized,
    );
  }

  void _addTag(String rawTag) {
    final tag = rawTag.trim();
    if (tag.isEmpty || _isTagSelected(tag)) {
      _tagController.clear();
      return;
    }
    setState(() {
      _selectedTags = [..._selectedTags, tag];
      _tagController.clear();
    });
  }

  void _commitPendingTag() {
    final pendingTag = _tagController.text.trim();
    if (pendingTag.isEmpty) return;
    _addTag(pendingTag);
  }

  DateTime _initialDateForCreate(DateTime date) {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final selected = DateTime(date.year, date.month, date.day);
    if (selected == today) return now;
    return selected;
  }

  String _formatDate(DateTime date) {
    const months = [
      'Jan',
      'Feb',
      'Mar',
      'Apr',
      'May',
      'Jun',
      'Jul',
      'Aug',
      'Sep',
      'Oct',
      'Nov',
      'Dec',
    ];
    return '${date.day} ${months[date.month - 1]} ${date.year}';
  }

  Future<void> _selectDate() async {
    final pickedDate = await showDatePicker(
      context: context,
      initialDate: _selectedDate,
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
    );
    if (pickedDate != null) {
      setState(() => _selectedDate = _initialDateForCreate(pickedDate));
    }
  }

  Future<void> _saveTransaction() async {
    if (!_formKey.currentState!.validate()) return;
    _commitPendingTag();
    if (_selectedAccountId == null || _selectedCategoryId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please select an account and category')),
      );
      return;
    }

    setState(() => _isSaving = true);
    try {
      final request = TransactionCreateRequest(
        accountId: _selectedAccountId!,
        categoryId: _selectedCategoryId!,
        amount: double.parse(_amountController.text),
        description: _descriptionController.text.trim().isEmpty
            ? null
            : _descriptionController.text.trim(),
        tags: _selectedTags.isEmpty ? null : _selectedTags,
        createdAt: _selectedDate,
      );

      if (_isEditing) {
        await _transactionService.updateTransaction(
          widget.transactionId!,
          request,
        );
      } else {
        await _transactionService.createTransaction(request);
      }
      if (!mounted) return;
      Navigator.pop(context, true);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Failed to save transaction: $e')));
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  Future<void> _deleteTransaction() async {
    if (!_isEditing) return;
    final confirmed = await showDeleteDialog(
      context: context,
      resourceName: 'transaction',
    );
    if (!confirmed || !mounted) return;
    try {
      await _transactionService.deleteTransaction(widget.transactionId!);
      if (!mounted) return;
      Navigator.pop(context, true);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to delete transaction: $e')),
      );
    }
  }

  @override
  void dispose() {
    _descriptionController.dispose();
    _amountController.dispose();
    _tagController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;

    return Scaffold(
      appBar: AppBar(
        title: Text(_isEditing ? 'Edit Transaction' : 'New Transaction'),
        actions: [
          if (_isEditing)
            IconButton(
              icon: Icon(Icons.delete_outline, color: colorScheme.error),
              tooltip: 'Delete',
              onPressed: _deleteTransaction,
            ),
        ],
      ),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: AppTheme.screenPadding,
          children: [
            // ── Type selector ─────────────────────────────────────────
            Text(
              'Type',
              style: textTheme.labelLarge?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: AppTheme.space8),
            SegmentedButton<CategoryType>(
              segments: const [
                ButtonSegment(
                  value: CategoryType.expense,
                  label: Text('Expense'),
                  icon: Icon(Icons.arrow_upward_rounded, size: 16),
                ),
                ButtonSegment(
                  value: CategoryType.income,
                  label: Text('Income'),
                  icon: Icon(Icons.arrow_downward_rounded, size: 16),
                ),
              ],
              selected: {_transactionType},
              onSelectionChanged: (selection) => setState(() {
                _transactionType = selection.first;
                _selectedCategoryId = null;
              }),
            ),
            const SizedBox(height: AppTheme.space16),

            // ── Amount ────────────────────────────────────────────────
            TextFormField(
              controller: _amountController,
              decoration: InputDecoration(
                labelText: 'Amount',
                prefixIcon: const Icon(Icons.attach_money_outlined),
                suffixText: _selectedCurrencyCode.isEmpty
                    ? null
                    : _selectedCurrencyCode,
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

            // ── Description ───────────────────────────────────────────
            TextFormField(
              controller: _descriptionController,
              decoration: const InputDecoration(
                labelText: 'Description (optional)',
                prefixIcon: Icon(Icons.notes_outlined),
              ),
              textCapitalization: TextCapitalization.sentences,
            ),
            const SizedBox(height: AppTheme.space16),

            TypeAheadField<String>(
              controller: _tagController,
              builder: (context, controller, focusNode) {
                return TextFormField(
                  controller: controller,
                  focusNode: focusNode,
                  decoration: InputDecoration(
                    labelText: 'Tags (optional)',
                    prefixIcon: const Icon(Icons.sell_outlined),
                    hintText: 'Type tag and press enter',
                    suffixIcon: IconButton(
                      icon: const Icon(Icons.add_circle_outline),
                      onPressed: () => _addTag(controller.text),
                    ),
                  ),
                  textInputAction: TextInputAction.done,
                  onFieldSubmitted: _addTag,
                );
              },
              suggestionsCallback: (pattern) {
                final normalizedPattern = _normalizeTag(pattern);
                if (normalizedPattern.isEmpty) return const <String>[];
                return _allTags.where((tag) {
                  final normalizedTag = _normalizeTag(tag);
                  return normalizedTag.contains(normalizedPattern) &&
                      !_isTagSelected(tag);
                }).toList();
              },
              itemBuilder: (context, suggestion) {
                return ListTile(title: Text(suggestion));
              },
              onSelected: _addTag,
            ),
            if (_selectedTags.isNotEmpty) ...[
              const SizedBox(height: AppTheme.space8),
              Wrap(
                spacing: AppTheme.space8,
                runSpacing: AppTheme.space8,
                children: _selectedTags
                    .map(
                      (tag) => InputChip(
                        label: Text(tag),
                        onDeleted: () {
                          setState(() {
                            _selectedTags.remove(tag);
                          });
                        },
                      ),
                    )
                    .toList(),
              ),
            ],
            const SizedBox(height: AppTheme.space16),

            // ── Date ──────────────────────────────────────────────────
            InkWell(
              onTap: _selectDate,
              borderRadius: AppTheme.borderRadiusSmall,
              child: InputDecorator(
                decoration: const InputDecoration(
                  labelText: 'Date',
                  prefixIcon: Icon(Icons.calendar_today_outlined),
                  suffixIcon: Icon(Icons.edit_calendar_outlined),
                ),
                child: Text(
                  _formatDate(_selectedDate),
                  style: textTheme.bodyLarge,
                ),
              ),
            ),
            const SizedBox(height: AppTheme.space16),

            // ── Account dropdown ──────────────────────────────────────
            FutureBuilder<AccountsResult>(
              future: _futureAccounts,
              builder: (context, snapshot) {
                if (snapshot.hasData) {
                  final accounts = snapshot.data!.accounts;
                  if (_accounts.isEmpty && accounts.isNotEmpty) {
                    // Cache accounts list for currency lookup without setState.
                    _accounts = accounts;
                  }
                  return DropdownButtonFormField<int>(
                    initialValue: _selectedAccountId,
                    decoration: const InputDecoration(
                      labelText: 'Account',
                      prefixIcon: Icon(Icons.account_balance_outlined),
                    ),
                    items: accounts.map((account) {
                      return DropdownMenuItem<int>(
                        value: account.id,
                        child: Text(account.name),
                      );
                    }).toList(),
                    onChanged: (value) => setState(() {
                      _selectedAccountId = value;
                    }),
                    validator: (value) =>
                        value == null ? 'Please select an account' : null,
                  );
                } else if (snapshot.hasError) {
                  return Text(
                    'Failed to load accounts',
                    style: TextStyle(color: colorScheme.error),
                  );
                }
                return const Center(
                  child: Padding(
                    padding: EdgeInsets.all(AppTheme.space16),
                    child: CircularProgressIndicator(),
                  ),
                );
              },
            ),
            const SizedBox(height: AppTheme.space16),

            // ── Category dropdown ─────────────────────────────────────
            FutureBuilder<List<Category>>(
              future: _futureCategories,
              builder: (context, snapshot) {
                if (snapshot.hasData) {
                  final filtered = snapshot.data!
                      .where((cat) => cat.type == _transactionType)
                      .toList();
                  return DropdownButtonFormField<int>(
                    initialValue: _selectedCategoryId,
                    decoration: const InputDecoration(
                      labelText: 'Category',
                      prefixIcon: Icon(Icons.folder_outlined),
                    ),
                    items: filtered.map((category) {
                      return DropdownMenuItem<int>(
                        value: category.id,
                        child: Text(category.name),
                      );
                    }).toList(),
                    onChanged: (value) =>
                        setState(() => _selectedCategoryId = value),
                    validator: (value) =>
                        value == null ? 'Please select a category' : null,
                  );
                } else if (snapshot.hasError) {
                  return Text(
                    'Failed to load categories',
                    style: TextStyle(color: colorScheme.error),
                  );
                }
                return const Center(
                  child: Padding(
                    padding: EdgeInsets.all(AppTheme.space16),
                    child: CircularProgressIndicator(),
                  ),
                );
              },
            ),
            const SizedBox(height: AppTheme.space32),

            // ── Save button ───────────────────────────────────────────
            FilledButton(
              onPressed: _isSaving ? null : _saveTransaction,
              child: _isSaving
                  ? const AppLoadingSpinner()
                  : Text(_isEditing ? 'Save Changes' : 'Add Transaction'),
            ),
          ],
        ),
      ),
    );
  }
}
