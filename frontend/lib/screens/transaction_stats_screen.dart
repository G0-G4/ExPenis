import 'package:flutter/material.dart';

import 'package:fl_chart/fl_chart.dart';

import 'package:expenis_mobile/models/category.dart';
import 'package:expenis_mobile/models/transaction.dart';
import 'package:expenis_mobile/screens/edit_transaction_screen.dart';
import 'package:expenis_mobile/service/category_service.dart';
import 'package:expenis_mobile/service/transaction_service.dart';
import 'package:expenis_mobile/theme.dart';
import 'package:expenis_mobile/utils/format.dart';
import 'package:expenis_mobile/widgets/app_empty_state.dart';
import 'package:expenis_mobile/widgets/app_error_state.dart';

class TransactionStatsScreen extends StatefulWidget {
  const TransactionStatsScreen({super.key, required this.initialEndDate});

  final DateTime initialEndDate;

  @override
  State<TransactionStatsScreen> createState() => _TransactionStatsScreenState();
}

class _TransactionStatsScreenState extends State<TransactionStatsScreen> {
  final TransactionService _transactionService = TransactionService();
  final CategoryService _categoryService = CategoryService();

  late DateTime _startDate;
  late DateTime _endDate;

  List<Transaction> _transactions = [];
  List<Category> _categories = [];
  Set<int> _selectedIncomeCategoryIds = {};
  Set<int> _selectedExpenseCategoryIds = {};
  Map<String, String> _availableIncomeTagsByNormalized = {};
  Map<String, String> _availableExpenseTagsByNormalized = {};
  Set<String> _selectedIncomeTagKeys = {};
  Set<String> _selectedExpenseTagKeys = {};
  bool _hasInitializedSelections = false;
  bool _hasInitializedIncomeTagSelections = false;
  bool _hasInitializedExpenseTagSelections = false;
  bool _isFirstLoad = true;
  bool _isLoading = false;
  String? _loadError;

  String _normalizeTag(String tag) => tag.trim().toLowerCase();

  @override
  void initState() {
    super.initState();
    _endDate = DateTime(
      widget.initialEndDate.year,
      widget.initialEndDate.month,
      widget.initialEndDate.day,
    );
    _startDate = DateTime(_endDate.year, _endDate.month, 1);
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() {
      _isLoading = true;
      _loadError = null;
    });

    try {
      final results = await Future.wait([
        _transactionService.fetchTransactions(
          dateFrom: _startDate,
          dateTo: _endDate,
        ),
        _categoryService.fetchCategories(),
      ]);

      if (!mounted) return;
      final transactions = results[0] as List<Transaction>;
      final categories = results[1] as List<Category>;
      final incomeTagsByNormalized = <String, String>{};
      final expenseTagsByNormalized = <String, String>{};

      final usedIncomeCategoryIds = <int>{};
      final usedExpenseCategoryIds = <int>{};

      for (final transaction in transactions) {
        if (transaction.type == TransactionType.income) {
          usedIncomeCategoryIds.add(transaction.categoryId);
        } else {
          usedExpenseCategoryIds.add(transaction.categoryId);
        }

        for (final tag in transaction.tags) {
          final cleanedTag = tag.trim();
          if (cleanedTag.isEmpty) continue;
          final normalized = _normalizeTag(cleanedTag);
          if (transaction.type == TransactionType.income) {
            incomeTagsByNormalized.putIfAbsent(normalized, () => cleanedTag);
          } else {
            expenseTagsByNormalized.putIfAbsent(normalized, () => cleanedTag);
          }
        }
      }

      final incomeIds = categories
          .where((c) => c.type == CategoryType.income)
          .map((c) => c.id)
          .toSet()
          .intersection(usedIncomeCategoryIds);
      final expenseIds = categories
          .where((c) => c.type == CategoryType.expense)
          .map((c) => c.id)
          .toSet()
          .intersection(usedExpenseCategoryIds);

      setState(() {
        _transactions = transactions;
        _categories = categories;
        if (!_hasInitializedSelections) {
          _selectedIncomeCategoryIds = incomeIds;
          _selectedExpenseCategoryIds = expenseIds;
          _hasInitializedSelections = true;
        } else {
          final nextIncomeSelection = _selectedIncomeCategoryIds.intersection(
            incomeIds,
          );
          final nextExpenseSelection = _selectedExpenseCategoryIds.intersection(
            expenseIds,
          );

          _selectedIncomeCategoryIds = nextIncomeSelection.isEmpty
              ? incomeIds
              : nextIncomeSelection;
          _selectedExpenseCategoryIds = nextExpenseSelection.isEmpty
              ? expenseIds
              : nextExpenseSelection;
        }

        _availableIncomeTagsByNormalized = incomeTagsByNormalized;
        _availableExpenseTagsByNormalized = expenseTagsByNormalized;

        if (!_hasInitializedIncomeTagSelections) {
          _selectedIncomeTagKeys = <String>{};
          _hasInitializedIncomeTagSelections = true;
        } else {
          _selectedIncomeTagKeys = _selectedIncomeTagKeys.intersection(
            incomeTagsByNormalized.keys.toSet(),
          );
        }

        if (!_hasInitializedExpenseTagSelections) {
          _selectedExpenseTagKeys = <String>{};
          _hasInitializedExpenseTagSelections = true;
        } else {
          _selectedExpenseTagKeys = _selectedExpenseTagKeys.intersection(
            expenseTagsByNormalized.keys.toSet(),
          );
        }

        _isLoading = false;
        _isFirstLoad = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loadError = e.toString();
        _isLoading = false;
        _isFirstLoad = false;
      });
    }
  }

  Future<void> _selectStartDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _startDate,
      firstDate: DateTime(2000),
      lastDate: _endDate,
    );
    if (picked == null || !mounted) return;
    setState(() {
      _startDate = picked;
    });
    _resetFiltersForReload();
    _loadData();
  }

  Future<void> _selectEndDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _endDate,
      firstDate: _startDate,
      lastDate: DateTime(2100),
    );
    if (picked == null || !mounted) return;
    setState(() {
      _endDate = picked;
    });
    _resetFiltersForReload();
    _loadData();
  }

  void _resetFiltersForReload() {
    _hasInitializedSelections = false;
    _hasInitializedIncomeTagSelections = false;
    _hasInitializedExpenseTagSelections = false;
    _selectedIncomeCategoryIds = {};
    _selectedExpenseCategoryIds = {};
    _selectedIncomeTagKeys = {};
    _selectedExpenseTagKeys = {};
  }

  void _toggleIncomeCategory(int id) {
    setState(() {
      if (_selectedIncomeCategoryIds.contains(id)) {
        _selectedIncomeCategoryIds.remove(id);
      } else {
        _selectedIncomeCategoryIds.add(id);
      }
    });
  }

  void _toggleExpenseCategory(int id) {
    setState(() {
      if (_selectedExpenseCategoryIds.contains(id)) {
        _selectedExpenseCategoryIds.remove(id);
      } else {
        _selectedExpenseCategoryIds.add(id);
      }
    });
  }

  void _setIncomeCategorySelection(Set<int> ids) {
    setState(() {
      _selectedIncomeCategoryIds = ids;
    });
  }

  void _setExpenseCategorySelection(Set<int> ids) {
    setState(() {
      _selectedExpenseCategoryIds = ids;
    });
  }

  void _toggleIncomeTag(String tagKey) {
    setState(() {
      if (_selectedIncomeTagKeys.contains(tagKey)) {
        _selectedIncomeTagKeys.remove(tagKey);
      } else {
        _selectedIncomeTagKeys.add(tagKey);
      }
    });
  }

  void _toggleExpenseTag(String tagKey) {
    setState(() {
      if (_selectedExpenseTagKeys.contains(tagKey)) {
        _selectedExpenseTagKeys.remove(tagKey);
      } else {
        _selectedExpenseTagKeys.add(tagKey);
      }
    });
  }

  void _setIncomeTagSelection(Set<String> keys) {
    setState(() {
      _selectedIncomeTagKeys = keys;
    });
  }

  void _setExpenseTagSelection(Set<String> keys) {
    setState(() {
      _selectedExpenseTagKeys = keys;
    });
  }

  bool _matchesTagFilter(Transaction transaction, Set<String> selectedTagKeys) {
    if (selectedTagKeys.isEmpty) return true;
    for (final tag in transaction.tags) {
      if (selectedTagKeys.contains(_normalizeTag(tag))) {
        return true;
      }
    }
    return false;
  }

  Future<void> _openEdit(Transaction transaction) async {
    final result = await Navigator.push<bool>(
      context,
      MaterialPageRoute(
        builder: (context) =>
            EditTransactionScreen(transactionId: transaction.id),
      ),
    );
    if (!mounted) return;
    if (result == true) {
      _resetFiltersForReload();
      _loadData();
    }
  }

  String _formatDate(DateTime date) {
    const months = [
      "Jan",
      "Feb",
      "Mar",
      "Apr",
      "May",
      "Jun",
      "Jul",
      "Aug",
      "Sep",
      "Oct",
      "Nov",
      "Dec",
    ];
    return "${date.day} ${months[date.month - 1]} ${date.year}";
  }

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;

    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(title: const Text("Statistics")),
        body: SafeArea(
          top: false,
          bottom: true,
          child: Column(
            children: [
              _DateRangeBar(
                startDateLabel: _formatDate(_startDate),
                endDateLabel: _formatDate(_endDate),
                onStartTap: _selectStartDate,
                onEndTap: _selectEndDate,
              ),
              AnimatedContainer(
                duration: const Duration(milliseconds: 150),
                height: _isLoading ? 2.0 : 0.0,
                child: _isLoading
                    ? const LinearProgressIndicator()
                    : const SizedBox.shrink(),
              ),
              TabBar(
                labelStyle: textTheme.labelLarge?.copyWith(
                  fontWeight: FontWeight.w700,
                ),
                labelColor: colorScheme.onSurface,
                unselectedLabelColor: colorScheme.onSurfaceVariant,
                indicatorColor: colorScheme.primary,
                tabs: const [
                  Tab(text: "Income"),
                  Tab(text: "Expenses"),
                ],
              ),
              Expanded(
                child: _isFirstLoad && _isLoading
                    ? const Center(child: CircularProgressIndicator())
                    : _buildContent(),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildContent() {
    if (_loadError != null) {
      return AppErrorState(message: _loadError!, onRetry: _loadData);
    }

    if (_transactions.isEmpty) {
      return const AppEmptyState(
        icon: Icons.pie_chart_outline_rounded,
        title: "No transactions",
        subtitle: "There are no transactions in this range",
      );
    }

    final income = _transactions
        .where((t) => t.type == TransactionType.income)
        .where((t) => _selectedIncomeCategoryIds.contains(t.categoryId))
        .where((t) => _matchesTagFilter(t, _selectedIncomeTagKeys))
        .toList();
    final expense = _transactions
        .where((t) => t.type == TransactionType.expense)
        .where((t) => _selectedExpenseCategoryIds.contains(t.categoryId))
        .where((t) => _matchesTagFilter(t, _selectedExpenseTagKeys))
        .toList();

    final sortedIncomeTagKeys = _availableIncomeTagsByNormalized.keys.toList()
      ..sort(
        (a, b) => _availableIncomeTagsByNormalized[a]!.toLowerCase().compareTo(
          _availableIncomeTagsByNormalized[b]!.toLowerCase(),
        ),
      );
    final sortedExpenseTagKeys = _availableExpenseTagsByNormalized.keys.toList()
      ..sort(
        (a, b) => _availableExpenseTagsByNormalized[a]!.toLowerCase().compareTo(
          _availableExpenseTagsByNormalized[b]!.toLowerCase(),
        ),
      );

    final incomeCategories = _categories
        .where((c) => c.type == CategoryType.income)
        .where(
          (c) => _transactions.any(
            (t) => t.type == TransactionType.income && t.categoryId == c.id,
          ),
        )
        .toList();

    final expenseCategories = _categories
        .where((c) => c.type == CategoryType.expense)
        .where(
          (c) => _transactions.any(
            (t) => t.type == TransactionType.expense && t.categoryId == c.id,
          ),
        )
        .toList();

    final incomeTotal = income.fold<double>(0, (s, t) => s + t.amountRubles);
    final expenseTotal = expense.fold<double>(0, (s, t) => s + t.amountRubles);
    final net = incomeTotal - expenseTotal;

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(
            AppTheme.space16,
            AppTheme.space16,
            AppTheme.space16,
            AppTheme.space8,
          ),
          child: _TotalSummaryCard(
            incomeTotal: incomeTotal,
            expenseTotal: expenseTotal,
            netTotal: net,
          ),
        ),
        Expanded(
          child: TabBarView(
            children: [
              ListView(
                padding: AppTheme.screenPadding,
                children: [
                  _CategorySection(
                    title: "Income by Category",
                    color: AppTheme.incomeColor,
                    icon: Icons.arrow_downward_rounded,
                    palette: _PieColors.incomePalette,
                    chartData: _buildCategoryTotals(income),
                    emptyLabel: "No income in selected categories",
                  ),
                  const SizedBox(height: AppTheme.space24),
                  _FiltersAccordion(
                    accentColor: AppTheme.incomeColor,
                    categories: incomeCategories,
                    selectedCategoryIds: _selectedIncomeCategoryIds,
                    onToggleCategory: _toggleIncomeCategory,
                    onSetCategorySelection: _setIncomeCategorySelection,
                    availableTagKeys: sortedIncomeTagKeys,
                    tagLabelsByKey: _availableIncomeTagsByNormalized,
                    selectedTagKeys: _selectedIncomeTagKeys,
                    onToggleTag: _toggleIncomeTag,
                    onSetTagSelection: _setIncomeTagSelection,
                  ),
                  const SizedBox(height: AppTheme.space24),
                  _TransactionsSection(
                    title: "Income transactions",
                    color: AppTheme.incomeColor,
                    icon: Icons.arrow_downward_rounded,
                    transactions: income,
                    onTap: _openEdit,
                  ),
                ],
              ),
              ListView(
                padding: AppTheme.screenPadding,
                children: [
                  _CategorySection(
                    title: "Expenses by Category",
                    color: AppTheme.expenseColor,
                    icon: Icons.arrow_upward_rounded,
                    palette: _PieColors.expensePalette,
                    chartData: _buildCategoryTotals(expense),
                    emptyLabel: "No expenses in selected categories",
                  ),
                  const SizedBox(height: AppTheme.space24),
                  _FiltersAccordion(
                    accentColor: AppTheme.expenseColor,
                    categories: expenseCategories,
                    selectedCategoryIds: _selectedExpenseCategoryIds,
                    onToggleCategory: _toggleExpenseCategory,
                    onSetCategorySelection: _setExpenseCategorySelection,
                    availableTagKeys: sortedExpenseTagKeys,
                    tagLabelsByKey: _availableExpenseTagsByNormalized,
                    selectedTagKeys: _selectedExpenseTagKeys,
                    onToggleTag: _toggleExpenseTag,
                    onSetTagSelection: _setExpenseTagSelection,
                  ),
                  const SizedBox(height: AppTheme.space24),
                  _TransactionsSection(
                    title: "Expense transactions",
                    color: AppTheme.expenseColor,
                    icon: Icons.arrow_upward_rounded,
                    transactions: expense,
                    onTap: _openEdit,
                  ),
                ],
              ),
            ],
          ),
        ),
      ],
    );
  }

  List<_CategoryTotal> _buildCategoryTotals(List<Transaction> items) {
    final totalsById = <int, _CategoryTotal>{};
    for (final item in items) {
      final name = item.category;
      final existing = totalsById[item.categoryId];
      if (existing == null) {
        totalsById[item.categoryId] = _CategoryTotal(
          categoryId: item.categoryId,
          name: name,
          total: item.amountRubles,
        );
      } else {
        totalsById[item.categoryId] = existing.copyWith(
          total: existing.total + item.amountRubles,
        );
      }
    }

    final totals = totalsById.values.toList();
    totals.sort((a, b) => b.total.compareTo(a.total));
    return totals;
  }
}

class _DateRangeBar extends StatelessWidget {
  const _DateRangeBar({
    required this.startDateLabel,
    required this.endDateLabel,
    required this.onStartTap,
    required this.onEndTap,
  });

  final String startDateLabel;
  final String endDateLabel;
  final VoidCallback onStartTap;
  final VoidCallback onEndTap;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return Container(
      color: colorScheme.surface,
      padding: const EdgeInsets.symmetric(
        horizontal: AppTheme.space16,
        vertical: AppTheme.space12,
      ),
      child: Row(
        children: [
          Expanded(
            child: _DateChip(
              label: "From",
              value: startDateLabel,
              onTap: onStartTap,
            ),
          ),
          const SizedBox(width: AppTheme.space12),
          Icon(
            Icons.arrow_forward_rounded,
            size: AppTheme.iconSizeMedium,
            color: colorScheme.onSurfaceVariant,
          ),
          const SizedBox(width: AppTheme.space12),
          Expanded(
            child: _DateChip(label: "To", value: endDateLabel, onTap: onEndTap),
          ),
        ],
      ),
    );
  }
}

class _DateChip extends StatelessWidget {
  const _DateChip({
    required this.label,
    required this.value,
    required this.onTap,
  });

  final String label;
  final String value;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    return InkWell(
      onTap: onTap,
      borderRadius: AppTheme.borderRadiusSmall,
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: AppTheme.space12,
          vertical: AppTheme.space8,
        ),
        decoration: BoxDecoration(
          color: colorScheme.surfaceContainerLowest,
          borderRadius: AppTheme.borderRadiusSmall,
          border: Border.all(color: colorScheme.outlineVariant),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              label,
              style: textTheme.labelSmall?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: AppTheme.space4),
            Text(
              value,
              style: textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _TotalSummaryCard extends StatelessWidget {
  const _TotalSummaryCard({
    required this.incomeTotal,
    required this.expenseTotal,
    required this.netTotal,
  });

  final double incomeTotal;
  final double expenseTotal;
  final double netTotal;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    final isPositive = netTotal >= 0;

    return Card(
      child: Padding(
        padding: AppTheme.cardPadding,
        child: Column(
          children: [
            Row(
              children: [
                _SummaryItem(
                  label: "Income",
                  amount: incomeTotal,
                  color: AppTheme.incomeColor,
                  bgColor: AppTheme.incomeColorLight,
                  icon: Icons.arrow_downward_rounded,
                ),
                Container(
                  width: 1,
                  height: 48,
                  color: colorScheme.outlineVariant,
                ),
                _SummaryItem(
                  label: "Expenses",
                  amount: expenseTotal,
                  color: AppTheme.expenseColor,
                  bgColor: AppTheme.expenseColorLight,
                  icon: Icons.arrow_upward_rounded,
                ),
              ],
            ),
            const SizedBox(height: AppTheme.space12),
            Divider(color: colorScheme.outlineVariant),
            const SizedBox(height: AppTheme.space8),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  "Net",
                  style: textTheme.bodyMedium?.copyWith(
                    color: colorScheme.onSurfaceVariant,
                  ),
                ),
                Text(
                  "${isPositive ? '+' : ''}${formatAmount(netTotal.abs())} ₽",
                  style: textTheme.titleMedium?.copyWith(
                    color: isPositive
                        ? AppTheme.incomeColor
                        : AppTheme.expenseColor,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _SummaryItem extends StatelessWidget {
  const _SummaryItem({
    required this.label,
    required this.amount,
    required this.color,
    required this.bgColor,
    required this.icon,
  });

  final String label;
  final double amount;
  final Color color;
  final Color bgColor;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final fmt = formatAmount(amount);

    return Expanded(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: AppTheme.space8),
        child: Row(
          children: [
            Container(
              width: AppTheme.iconBoxSizeSmall,
              height: AppTheme.iconBoxSizeSmall,
              decoration: BoxDecoration(
                color: bgColor,
                borderRadius: AppTheme.borderRadiusSmall,
              ),
              child: Icon(icon, size: AppTheme.iconSizeMedium, color: color),
            ),
            const SizedBox(width: AppTheme.space8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    label,
                    style: textTheme.labelSmall?.copyWith(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                  ),
                  Text(
                    "$fmt ₽",
                    style: textTheme.titleSmall?.copyWith(
                      color: color,
                      fontWeight: FontWeight.w700,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({
    required this.label,
    required this.color,
    required this.icon,
  });

  final String label;
  final Color color;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: AppTheme.iconSizeSmall, color: color),
        const SizedBox(width: AppTheme.space4),
        Text(
          label.toUpperCase(),
          style: Theme.of(context).textTheme.labelMedium?.copyWith(
            color: color,
            fontWeight: FontWeight.w700,
            letterSpacing: 0.8,
          ),
        ),
      ],
    );
  }
}

class _CategorySection extends StatelessWidget {
  const _CategorySection({
    required this.title,
    required this.color,
    required this.icon,
    required this.palette,
    required this.chartData,
    required this.emptyLabel,
  });

  final String title;
  final Color color;
  final IconData icon;
  final List<Color> palette;
  final List<_CategoryTotal> chartData;
  final String emptyLabel;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _SectionHeader(label: title, color: color, icon: icon),
        const SizedBox(height: AppTheme.space16),
        _PieChartCard(
          baseColor: color,
          palette: palette,
          data: chartData,
          emptyLabel: emptyLabel,
        ),
      ],
    );
  }
}

class _FiltersAccordion extends StatelessWidget {
  const _FiltersAccordion({
    required this.accentColor,
    required this.categories,
    required this.selectedCategoryIds,
    required this.onToggleCategory,
    required this.onSetCategorySelection,
    required this.availableTagKeys,
    required this.tagLabelsByKey,
    required this.selectedTagKeys,
    required this.onToggleTag,
    required this.onSetTagSelection,
  });

  final Color accentColor;
  final List<Category> categories;
  final Set<int> selectedCategoryIds;
  final ValueChanged<int> onToggleCategory;
  final ValueChanged<Set<int>> onSetCategorySelection;
  final List<String> availableTagKeys;
  final Map<String, String> tagLabelsByKey;
  final Set<String> selectedTagKeys;
  final ValueChanged<String> onToggleTag;
  final ValueChanged<Set<String>> onSetTagSelection;

  static const double _maxChipAreaHeight = 156;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    final categorySummary =
        "${selectedCategoryIds.length}/${categories.length} selected";
    final tagSummary =
        "${selectedTagKeys.length}/${availableTagKeys.length} selected";

    return Card(
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(
              AppTheme.space16,
              AppTheme.space12,
              AppTheme.space16,
              AppTheme.space4,
            ),
            child: Row(
              children: [
                Icon(Icons.tune_rounded, color: colorScheme.onSurfaceVariant),
                const SizedBox(width: AppTheme.space8),
                Text(
                  "Filters",
                  style: textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
          Divider(height: 1, color: colorScheme.outlineVariant),
          ExpansionTile(
            leading: Icon(Icons.folder_outlined, color: accentColor),
            title: const Text("Category filter"),
            subtitle: Text(categorySummary),
            shape: const Border(),
            collapsedShape: const Border(),
            childrenPadding: const EdgeInsets.fromLTRB(
              AppTheme.space16,
              0,
              AppTheme.space16,
              AppTheme.space16,
            ),
            children: [
              _FilterActions(
                onSelectAll: categories.isEmpty
                    ? null
                    : () => onSetCategorySelection(
                        categories.map((category) => category.id).toSet(),
                      ),
                onClearAll: selectedCategoryIds.isEmpty
                    ? null
                    : () => onSetCategorySelection(<int>{}),
              ),
              const SizedBox(height: AppTheme.space8),
              if (categories.isEmpty)
                Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    "No categories",
                    style: textTheme.bodySmall?.copyWith(
                      color: colorScheme.onSurfaceVariant,
                    ),
                  ),
                )
              else
                _buildScrollableChipArea(
                  child: Wrap(
                    spacing: AppTheme.space8,
                    runSpacing: AppTheme.space8,
                    children: categories
                        .map(
                          (category) => FilterChip(
                            label: Text(category.name),
                            selected: selectedCategoryIds.contains(category.id),
                            onSelected: (_) => onToggleCategory(category.id),
                            showCheckmark: false,
                            selectedColor: accentColor.withAlpha(30),
                            backgroundColor: colorScheme.surfaceContainerLow,
                            checkmarkColor: accentColor,
                            side: BorderSide(color: colorScheme.outlineVariant),
                            labelStyle: textTheme.labelMedium?.copyWith(
                              color: selectedCategoryIds.contains(category.id)
                                  ? accentColor
                                  : colorScheme.onSurface,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        )
                        .toList(),
                  ),
                ),
            ],
          ),
          Divider(height: 1, color: colorScheme.outlineVariant),
          ExpansionTile(
            leading: Icon(Icons.sell_outlined, color: accentColor),
            title: const Text("Tag filter"),
            subtitle: Text(tagSummary),
            shape: const Border(),
            collapsedShape: const Border(),
            childrenPadding: const EdgeInsets.fromLTRB(
              AppTheme.space16,
              0,
              AppTheme.space16,
              AppTheme.space16,
            ),
            children: [
              _FilterActions(
                onSelectAll: availableTagKeys.isEmpty
                    ? null
                    : () => onSetTagSelection(availableTagKeys.toSet()),
                onClearAll: selectedTagKeys.isEmpty
                    ? null
                    : () => onSetTagSelection(<String>{}),
              ),
              const SizedBox(height: AppTheme.space8),
              if (availableTagKeys.isEmpty)
                Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    "No tags in selected range",
                    style: textTheme.bodySmall?.copyWith(
                      color: colorScheme.onSurfaceVariant,
                    ),
                  ),
                )
              else
                _buildScrollableChipArea(
                  child: Wrap(
                    spacing: AppTheme.space8,
                    runSpacing: AppTheme.space8,
                    children: availableTagKeys
                        .map(
                          (tagKey) => FilterChip(
                            label: Text(tagLabelsByKey[tagKey] ?? tagKey),
                            selected: selectedTagKeys.contains(tagKey),
                            onSelected: (_) => onToggleTag(tagKey),
                            showCheckmark: false,
                            selectedColor: accentColor.withAlpha(30),
                            backgroundColor: colorScheme.surfaceContainerLow,
                            checkmarkColor: accentColor,
                            side: BorderSide(color: colorScheme.outlineVariant),
                            labelStyle: textTheme.labelMedium?.copyWith(
                              color: selectedTagKeys.contains(tagKey)
                                  ? accentColor
                                  : colorScheme.onSurface,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        )
                        .toList(),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildScrollableChipArea({required Widget child}) {
    return ConstrainedBox(
      constraints: const BoxConstraints(maxHeight: _maxChipAreaHeight),
      child: Scrollbar(
        child: SingleChildScrollView(
          child: Align(alignment: Alignment.topLeft, child: child),
        ),
      ),
    );
  }
}

class _FilterActions extends StatelessWidget {
  const _FilterActions({required this.onSelectAll, required this.onClearAll});

  final VoidCallback? onSelectAll;
  final VoidCallback? onClearAll;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        TextButton.icon(
          onPressed: onSelectAll,
          icon: const Icon(
            Icons.done_all_rounded,
            size: AppTheme.iconSizeSmall,
          ),
          label: const Text("Select all"),
        ),
        const SizedBox(width: AppTheme.space4),
        TextButton.icon(
          onPressed: onClearAll,
          icon: const Icon(
            Icons.clear_all_rounded,
            size: AppTheme.iconSizeSmall,
          ),
          label: const Text("Clear all"),
        ),
      ],
    );
  }
}

class _PieChartCard extends StatelessWidget {
  const _PieChartCard({
    required this.baseColor,
    required this.palette,
    required this.data,
    required this.emptyLabel,
  });

  static const double _minSlicePercent = 1;
  static const double _chartHeight = 220;
  static const double _legendHeight = 172;
  static const double _bodyHeight = 420;

  final Color baseColor;
  final List<Color> palette;
  final List<_CategoryTotal> data;
  final String emptyLabel;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final colorScheme = Theme.of(context).colorScheme;

    return Card(
      child: Padding(
        padding: AppTheme.cardPadding,
        child: SizedBox(
          height: _bodyHeight,
          child: data.isEmpty
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.pie_chart_outline_rounded,
                        color: colorScheme.onSurfaceVariant,
                        size: 32,
                      ),
                      const SizedBox(height: AppTheme.space8),
                      Text(
                        emptyLabel,
                        style: textTheme.bodySmall?.copyWith(
                          color: colorScheme.onSurfaceVariant,
                        ),
                        textAlign: TextAlign.center,
                      ),
                    ],
                  ),
                )
              : Column(
                  children: [
                    SizedBox(
                      height: _chartHeight,
                      child: PieChart(
                        PieChartData(
                          sections: _buildSections(data),
                          centerSpaceRadius: 52,
                          sectionsSpace: 2,
                        ),
                      ),
                    ),
                    const SizedBox(height: AppTheme.space16),
                    SizedBox(
                      height: _legendHeight,
                      child: Scrollbar(
                        child: SingleChildScrollView(
                          child: Column(
                            children: data
                                .map(
                                  (item) => Padding(
                                    padding: const EdgeInsets.only(
                                      bottom: AppTheme.space8,
                                    ),
                                    child: _LegendRow(
                                      color: item.color,
                                      label: item.name,
                                      value: "${formatAmount(item.total)} ₽",
                                    ),
                                  ),
                                )
                                .toList(),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
        ),
      ),
    );
  }

  List<PieChartSectionData> _buildSections(List<_CategoryTotal> totals) {
    final totalValue = totals.fold<double>(0, (sum, item) => sum + item.total);
    if (totalValue == 0) return [];

    final colors = totals.length > 1 ? palette : [baseColor];
    final visibleTotals = totals
        .where((item) => item.total / totalValue * 100 >= _minSlicePercent)
        .toList();
    final sliceTotals = visibleTotals.isEmpty ? totals : visibleTotals;

    return sliceTotals.asMap().entries.map((entry) {
      final index = entry.key;
      final item = entry.value;
      final color = colors[index % colors.length];
      item.color = color;
      final value = item.total;
      final percentage = value / totalValue * 100;
      return PieChartSectionData(
        color: color,
        value: value,
        radius: 72,
        title: "${percentage.toStringAsFixed(0)}%",
        titleStyle: const TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w600,
          color: Colors.white,
        ),
      );
    }).toList();
  }
}

class _LegendRow extends StatelessWidget {
  const _LegendRow({
    required this.color,
    required this.label,
    required this.value,
  });

  final Color color;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final colorScheme = Theme.of(context).colorScheme;

    return Row(
      children: [
        Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: AppTheme.space8),
        Expanded(
          child: Text(
            label,
            style: textTheme.bodySmall?.copyWith(color: colorScheme.onSurface),
          ),
        ),
        Text(
          value,
          style: textTheme.bodySmall?.copyWith(fontWeight: FontWeight.w600),
        ),
      ],
    );
  }
}

class _CategoryTotal {
  _CategoryTotal({
    required this.categoryId,
    required this.name,
    required this.total,
    this.color = Colors.grey,
  });

  final int categoryId;
  final String name;
  final double total;
  Color color;

  _CategoryTotal copyWith({double? total}) {
    return _CategoryTotal(
      categoryId: categoryId,
      name: name,
      total: total ?? this.total,
      color: color,
    );
  }
}

class _PieColors {
  static const List<Color> incomePalette = [
    Color(0xFF2E7D32),
    Color(0xFF00897B),
    Color(0xFF0097A7),
    Color(0xFF1976D2),
    Color(0xFF7CB342),
    Color(0xFF43A047),
    Color(0xFF00ACC1),
    Color(0xFF5C6BC0),
    Color(0xFFAFB42B),
    Color(0xFF7E57C2),
    Color(0xFFFFB300),
    Color(0xFF26A69A),
  ];

  static const List<Color> expensePalette = [
    Color(0xFFC62828),
    Color(0xFFD32F2F),
    Color(0xFFF4511E),
    Color(0xFFFF7043),
    Color(0xFF8E24AA),
    Color(0xFFEC407A),
    Color(0xFF6D4C41),
    Color(0xFFFF8F00),
    Color(0xFF5D4037),
    Color(0xFFFFA000),
    Color(0xFFAD1457),
    Color(0xFFEF5350),
  ];
}

class _TransactionsSection extends StatelessWidget {
  const _TransactionsSection({
    required this.title,
    required this.color,
    required this.icon,
    required this.transactions,
    required this.onTap,
  });

  final String title;
  final Color color;
  final IconData icon;
  final List<Transaction> transactions;
  final ValueChanged<Transaction> onTap;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final colorScheme = Theme.of(context).colorScheme;
    final grouped = _groupTransactions(transactions);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _SectionHeader(label: title, color: color, icon: icon),
        const SizedBox(height: AppTheme.space8),
        if (transactions.isEmpty)
          Text(
            "No transactions",
            style: textTheme.bodySmall?.copyWith(
              color: colorScheme.onSurfaceVariant,
            ),
          )
        else
          ...grouped.expand(
            (group) => [
              _DateHeader(label: _formatGroupLabel(group.date)),
              const SizedBox(height: AppTheme.space8),
              ...group.transactions.map(
                (transaction) => Padding(
                  padding: const EdgeInsets.only(bottom: AppTheme.space8),
                  child: _TransactionCard(
                    transaction: transaction,
                    onTap: () => onTap(transaction),
                  ),
                ),
              ),
              const SizedBox(height: AppTheme.space8),
            ],
          ),
      ],
    );
  }

  List<_DateGroup> _groupTransactions(List<Transaction> items) {
    final groups = <DateTime, List<Transaction>>{};
    final unknown = <Transaction>[];

    for (final transaction in items) {
      final createdAt = transaction.createdAt;
      if (createdAt == null) {
        unknown.add(transaction);
      } else {
        final key = DateTime(createdAt.year, createdAt.month, createdAt.day);
        groups.putIfAbsent(key, () => []).add(transaction);
      }
    }

    for (final entry in groups.entries) {
      entry.value.sort((a, b) {
        final aTime = a.createdAt;
        final bTime = b.createdAt;
        if (aTime == null && bTime == null) return b.id.compareTo(a.id);
        if (aTime == null) return 1;
        if (bTime == null) return -1;
        return bTime.compareTo(aTime);
      });
    }
    unknown.sort((a, b) => b.id.compareTo(a.id));

    final sortedDates = groups.keys.toList()..sort((a, b) => b.compareTo(a));
    final result = <_DateGroup>[
      ...sortedDates.map(
        (date) => _DateGroup(date: date, transactions: groups[date] ?? []),
      ),
    ];

    if (unknown.isNotEmpty) {
      result.add(_DateGroup(date: null, transactions: unknown));
    }

    return result;
  }

  String _formatGroupLabel(DateTime? date) {
    if (date == null) return "Unknown date";
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    if (date == today) return "Today";
    if (date == today.subtract(const Duration(days: 1))) return "Yesterday";
    const months = [
      "Jan",
      "Feb",
      "Mar",
      "Apr",
      "May",
      "Jun",
      "Jul",
      "Aug",
      "Sep",
      "Oct",
      "Nov",
      "Dec",
    ];
    return "${date.day} ${months[date.month - 1]} ${date.year}";
  }
}

class _DateGroup {
  const _DateGroup({required this.date, required this.transactions});

  final DateTime? date;
  final List<Transaction> transactions;
}

class _DateHeader extends StatelessWidget {
  const _DateHeader({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    return Text(
      label,
      style: textTheme.labelLarge?.copyWith(
        color: colorScheme.onSurfaceVariant,
        fontWeight: FontWeight.w700,
        letterSpacing: 0.3,
      ),
    );
  }
}

class _TransactionCard extends StatelessWidget {
  const _TransactionCard({required this.transaction, required this.onTap});

  final Transaction transaction;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    final isIncome = transaction.type == TransactionType.income;
    final amountColor = isIncome ? AppTheme.incomeColor : AppTheme.expenseColor;
    final bgColor = isIncome
        ? AppTheme.incomeColorLight
        : AppTheme.expenseColorLight;
    final amountRublesStr = formatAmount(transaction.amountRubles);
    final showSecondary = transaction.currencyCode != "RUB";
    final nativeAmountStr = formatAmount(transaction.amount);

    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: AppTheme.borderRadiusMedium,
        child: Padding(
          padding: AppTheme.cardPadding,
          child: Row(
            children: [
              Container(
                width: AppTheme.iconBoxSize,
                height: AppTheme.iconBoxSize,
                decoration: BoxDecoration(
                  color: bgColor,
                  borderRadius: AppTheme.borderRadiusSmall,
                ),
                child: Icon(
                  isIncome
                      ? Icons.arrow_downward_rounded
                      : Icons.arrow_upward_rounded,
                  size: AppTheme.iconSizeMedium,
                  color: amountColor,
                ),
              ),
              const SizedBox(width: AppTheme.space12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      transaction.category,
                      style: textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: AppTheme.space2),
                    Row(
                      children: [
                        Icon(
                          Icons.account_balance_outlined,
                          size: AppTheme.iconSizeSmall,
                          color: colorScheme.onSurfaceVariant,
                        ),
                        const SizedBox(width: AppTheme.space4),
                        Text(
                          transaction.account,
                          style: textTheme.bodySmall?.copyWith(
                            color: colorScheme.onSurfaceVariant,
                          ),
                        ),
                        if (transaction.description != null &&
                            transaction.description!.isNotEmpty) ...[
                          Text(
                            " · ",
                            style: textTheme.bodySmall?.copyWith(
                              color: colorScheme.outlineVariant,
                            ),
                          ),
                          Flexible(
                            child: Text(
                              transaction.description!,
                              style: textTheme.bodySmall?.copyWith(
                                color: colorScheme.onSurfaceVariant,
                              ),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(width: AppTheme.space8),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    "${isIncome ? '+' : '-'}$amountRublesStr ₽",
                    style: textTheme.titleSmall?.copyWith(
                      color: amountColor,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  if (showSecondary)
                    Text(
                      "${isIncome ? '+' : '-'}$nativeAmountStr ${transaction.currencyCode}",
                      style: textTheme.bodySmall?.copyWith(
                        color: colorScheme.onSurfaceVariant,
                      ),
                    ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
