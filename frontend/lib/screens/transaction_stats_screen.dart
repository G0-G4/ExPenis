import 'package:flutter/material.dart';

import 'package:fl_chart/fl_chart.dart';

import 'package:expenis_mobile/models/category.dart';
import 'package:expenis_mobile/models/transaction.dart';
import 'package:expenis_mobile/screens/edit_transaction_screen.dart';
import 'package:expenis_mobile/service/category_service.dart';
import 'package:expenis_mobile/service/transaction_service.dart';
import 'package:expenis_mobile/theme.dart';
import 'package:expenis_mobile/utils/date_labels.dart';
import 'package:expenis_mobile/utils/format.dart';
import 'package:expenis_mobile/utils/selection_utils.dart';
import 'package:expenis_mobile/utils/tag_utils.dart';
import 'package:expenis_mobile/widgets/analytics_filters_card.dart';
import 'package:expenis_mobile/widgets/app_empty_state.dart';
import 'package:expenis_mobile/widgets/app_error_state.dart';
import 'package:expenis_mobile/widgets/month_picker_bottom_sheet.dart';

class TransactionStatsScreen extends StatefulWidget {
  const TransactionStatsScreen({
    super.key,
    required this.initialEndDate,
    this.initialGroupByMonth = false,
  });

  final DateTime initialEndDate;
  final bool initialGroupByMonth;

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
  List<DateTime> _months = [];

  Set<int> _availableIncomeCategoryIds = {};
  Set<int> _availableExpenseCategoryIds = {};
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
  bool _groupByMonth = false;
  String? _loadError;

  bool _isCurrentMonth(DateTime date) {
    final now = DateTime.now();
    return date.year == now.year && date.month == now.month;
  }

  DateTime _firstDayOfMonth(DateTime date) {
    return DateTime(date.year, date.month, 1);
  }

  DateTime _lastDayOfMonth(DateTime date) {
    return DateTime(date.year, date.month + 1, 0);
  }

  DateTime get _startMonth => DateTime(_startDate.year, _startDate.month, 1);

  DateTime get _endMonth => DateTime(_endDate.year, _endDate.month, 1);

  void _initializeGroupedRange() {
    final now = DateTime.now();
    _startDate = DateTime(now.year, now.month - 11, 1);
    _endDate = DateTime(now.year, now.month, now.day);
    _rebuildMonths();
  }

  void _rebuildMonths() {
    final months = <DateTime>[];
    var cursor = _startMonth;
    while (!cursor.isAfter(_endMonth)) {
      months.add(cursor);
      cursor = DateTime(cursor.year, cursor.month + 1, 1);
    }
    _months = months;
  }

  DateTime _groupedRangeEndDate() {
    final now = DateTime.now();
    if (_endMonth.year == now.year && _endMonth.month == now.month) {
      return DateTime(now.year, now.month, now.day);
    }
    return DateTime(_endMonth.year, _endMonth.month + 1, 0);
  }

  bool _isMonthInRange(DateTime date) {
    final normalized = DateTime(date.year, date.month, 1);
    return !normalized.isBefore(_startMonth) && !normalized.isAfter(_endMonth);
  }

  void _toggleGroupByMonth(bool value) {
    if (value == _groupByMonth) return;

    setState(() {
      _groupByMonth = value;
      if (_groupByMonth) {
        _initializeGroupedRange();
      } else {
        final pivot = _endDate;
        final monthStart = DateTime(pivot.year, pivot.month, 1);
        final monthEnd = _isCurrentMonth(pivot)
            ? DateTime.now()
            : DateTime(pivot.year, pivot.month + 1, 0);
        _startDate = monthStart;
        _endDate = DateTime(monthEnd.year, monthEnd.month, monthEnd.day);
      }
    });
    _resetFiltersForReload();
    _loadData();
  }

  void _applyMonthRange(DateTime monthDate) {
    final monthStart = _firstDayOfMonth(monthDate);
    final monthEnd = _isCurrentMonth(monthDate)
        ? DateTime.now()
        : _lastDayOfMonth(monthDate);
    setState(() {
      _startDate = monthStart;
      _endDate = DateTime(monthEnd.year, monthEnd.month, monthEnd.day);
    });
    _resetFiltersForReload();
    _loadData();
  }

  void _goToPreviousMonth() {
    _applyMonthRange(DateTime(_startDate.year, _startDate.month - 1, 1));
  }

  void _goToNextMonth() {
    if (_isCurrentMonth(_startDate)) return;
    final nextMonth = DateTime(_startDate.year, _startDate.month + 1, 1);
    final now = DateTime.now();
    final currentMonthStart = DateTime(now.year, now.month, 1);
    if (nextMonth.isAfter(currentMonthStart)) return;
    _applyMonthRange(nextMonth);
  }

  void _selectCurrentMonth() {
    _applyMonthRange(DateTime.now());
  }

  Future<void> _showMonthPickerSheet() async {
    final picked = await showMonthPickerBottomSheet(
      context: context,
      initialMonth: _startDate,
      titlePrefix: monthShortLabel(_startDate.month),
    );
    if (picked == null || !mounted) return;
    _applyMonthRange(DateTime(picked.year, picked.month, 1));
  }

  Future<void> _pickStartMonth() async {
    final picked = await _showGroupedMonthPicker(initialMonth: _startMonth);
    if (picked == null || !mounted) return;

    setState(() {
      _startDate = picked;
      if (_startMonth.isAfter(_endMonth)) {
        final adjustedEnd = _isCurrentMonth(picked)
            ? DateTime.now()
            : DateTime(picked.year, picked.month + 1, 0);
        _endDate = DateTime(
          adjustedEnd.year,
          adjustedEnd.month,
          adjustedEnd.day,
        );
      }
      _rebuildMonths();
    });
    _resetFiltersForReload();
    _loadData();
  }

  Future<void> _pickEndMonth() async {
    final picked = await _showGroupedMonthPicker(initialMonth: _endMonth);
    if (picked == null || !mounted) return;

    setState(() {
      final adjustedEnd = _isCurrentMonth(picked)
          ? DateTime.now()
          : DateTime(picked.year, picked.month + 1, 0);
      _endDate = DateTime(adjustedEnd.year, adjustedEnd.month, adjustedEnd.day);
      if (_endMonth.isBefore(_startMonth)) {
        _startDate = picked;
      }
      _rebuildMonths();
    });
    _resetFiltersForReload();
    _loadData();
  }

  Future<DateTime?> _showGroupedMonthPicker({
    required DateTime initialMonth,
  }) async {
    return showMonthPickerBottomSheet(
      context: context,
      initialMonth: initialMonth,
    );
  }

  @override
  void initState() {
    super.initState();
    _groupByMonth = widget.initialGroupByMonth;
    if (_groupByMonth) {
      _initializeGroupedRange();
    } else {
      _endDate = DateTime(
        widget.initialEndDate.year,
        widget.initialEndDate.month,
        widget.initialEndDate.day,
      );
      _startDate = DateTime(_endDate.year, _endDate.month, 1);
    }
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
          dateFrom: _groupByMonth ? _startMonth : _startDate,
          dateTo: _groupByMonth ? _groupedRangeEndDate() : _endDate,
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
          final normalized = normalizeTagKey(cleanedTag);
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
        _availableIncomeCategoryIds = incomeIds;
        _availableExpenseCategoryIds = expenseIds;
        if (!_hasInitializedSelections) {
          _selectedIncomeCategoryIds = incomeIds;
          _selectedExpenseCategoryIds = expenseIds;
          _hasInitializedSelections = true;
        } else {
          _selectedIncomeCategoryIds = intersectOrAll(
            _selectedIncomeCategoryIds,
            incomeIds,
          );
          _selectedExpenseCategoryIds = intersectOrAll(
            _selectedExpenseCategoryIds,
            expenseIds,
          );
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
      _selectedIncomeCategoryIds = toggledSetValue(
        _selectedIncomeCategoryIds,
        id,
      );
    });
  }

  void _toggleExpenseCategory(int id) {
    setState(() {
      _selectedExpenseCategoryIds = toggledSetValue(
        _selectedExpenseCategoryIds,
        id,
      );
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
      _selectedIncomeTagKeys = toggledSetValue(_selectedIncomeTagKeys, tagKey);
    });
  }

  void _toggleExpenseTag(String tagKey) {
    setState(() {
      _selectedExpenseTagKeys = toggledSetValue(
        _selectedExpenseTagKeys,
        tagKey,
      );
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
      if (selectedTagKeys.contains(normalizeTagKey(tag))) {
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
              Padding(
                padding: const EdgeInsets.fromLTRB(
                  AppTheme.space16,
                  AppTheme.space8,
                  AppTheme.space16,
                  AppTheme.space8,
                ),
                child: _StatsHeaderControls(
                  groupByMonth: _groupByMonth,
                  onGroupByMonthChanged: _toggleGroupByMonth,
                  monthLabel: formatMonthYearLabel(_startDate),
                  startDateLabel: formatDayMonthYearLabel(_startDate),
                  endDateLabel: formatDayMonthYearLabel(_endDate),
                  startMonthLabel: formatMonthYearLabel(_startMonth),
                  endMonthLabel: formatMonthYearLabel(_endMonth),
                  isOnCurrentMonth: _isCurrentMonth(_startDate),
                  onPreviousMonth: _goToPreviousMonth,
                  onNextMonth: _goToNextMonth,
                  onCurrentMonth: _selectCurrentMonth,
                  onMonthTap: _showMonthPickerSheet,
                  onStartTap: _selectStartDate,
                  onEndTap: _selectEndDate,
                  onPickStartMonth: _pickStartMonth,
                  onPickEndMonth: _pickEndMonth,
                ),
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

    if (_groupByMonth) {
      return _buildGroupedContent();
    }

    return _buildDetailedContent();
  }

  Widget _buildDetailedContent() {
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

    final incomeCategories = _incomeCategories;
    final expenseCategories = _expenseCategories;

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
                  AnalyticsFiltersCard(
                    accentColor: AppTheme.incomeColor,
                    categories: incomeCategories,
                    selectedCategoryIds: _selectedIncomeCategoryIds,
                    onToggleCategory: _toggleIncomeCategory,
                    onSetCategorySelection: _setIncomeCategorySelection,
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
                  AnalyticsFiltersCard(
                    accentColor: AppTheme.expenseColor,
                    categories: expenseCategories,
                    selectedCategoryIds: _selectedExpenseCategoryIds,
                    onToggleCategory: _toggleExpenseCategory,
                    onSetCategorySelection: _setExpenseCategorySelection,
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

  Widget _buildGroupedContent() {
    final monthPoints = _buildMonthPoints();
    final incomeStacked = _buildStackedMonthlyData(TransactionType.income);
    final expenseStacked = _buildStackedMonthlyData(TransactionType.expense);

    return TabBarView(
      children: [
        ListView(
          padding: AppTheme.screenPadding,
          children: [
            _MonthTrendCard(points: monthPoints),
            const SizedBox(height: AppTheme.space12),
            _StackedMonthlyBarCard(
              title: "Income by category",
              rows: incomeStacked.rows,
              legend: incomeStacked.legend,
              emptyLabel: "No income in selected range",
            ),
            const SizedBox(height: AppTheme.space12),
            AnalyticsFiltersCard(
              title: "Income filters",
              accentColor: AppTheme.incomeColor,
              categories: _incomeCategories,
              selectedCategoryIds: _selectedIncomeCategoryIds,
              onToggleCategory: _toggleIncomeCategory,
              onSetCategorySelection: _setIncomeCategorySelection,
              tagLabelsByKey: _availableIncomeTagsByNormalized,
              selectedTagKeys: _selectedIncomeTagKeys,
              onToggleTag: _toggleIncomeTag,
              onSetTagSelection: _setIncomeTagSelection,
            ),
          ],
        ),
        ListView(
          padding: AppTheme.screenPadding,
          children: [
            _MonthTrendCard(points: monthPoints),
            const SizedBox(height: AppTheme.space12),
            _StackedMonthlyBarCard(
              title: "Expenses by category",
              rows: expenseStacked.rows,
              legend: expenseStacked.legend,
              emptyLabel: "No expenses in selected range",
            ),
            const SizedBox(height: AppTheme.space12),
            AnalyticsFiltersCard(
              title: "Expense filters",
              accentColor: AppTheme.expenseColor,
              categories: _expenseCategories,
              selectedCategoryIds: _selectedExpenseCategoryIds,
              onToggleCategory: _toggleExpenseCategory,
              onSetCategorySelection: _setExpenseCategorySelection,
              tagLabelsByKey: _availableExpenseTagsByNormalized,
              selectedTagKeys: _selectedExpenseTagKeys,
              onToggleTag: _toggleExpenseTag,
              onSetTagSelection: _setExpenseTagSelection,
            ),
          ],
        ),
      ],
    );
  }

  bool _matchesFilters(Transaction transaction) {
    if (_groupByMonth) {
      final createdAt = transaction.createdAt;
      if (createdAt == null || !_isMonthInRange(createdAt)) return false;
    }

    final isIncome = transaction.type == TransactionType.income;
    final selectedCategoryIds = isIncome
        ? _selectedIncomeCategoryIds
        : _selectedExpenseCategoryIds;
    if (!selectedCategoryIds.contains(transaction.categoryId)) return false;

    final selectedTagKeys = isIncome
        ? _selectedIncomeTagKeys
        : _selectedExpenseTagKeys;
    return _matchesTagFilter(transaction, selectedTagKeys);
  }

  List<Transaction> get _filteredTransactions {
    return _transactions.where(_matchesFilters).toList();
  }

  List<_MonthPoint> _buildMonthPoints() {
    return _months.map((month) {
      double income = 0;
      double expense = 0;
      for (final transaction in _filteredTransactions) {
        final createdAt = transaction.createdAt;
        if (createdAt == null) continue;
        if (createdAt.year != month.year || createdAt.month != month.month) {
          continue;
        }
        if (transaction.type == TransactionType.income) {
          income += transaction.amountRubles;
        } else {
          expense += transaction.amountRubles;
        }
      }
      return _MonthPoint(month: month, income: income, expense: expense);
    }).toList();
  }

  _StackedChartData _buildStackedMonthlyData(TransactionType type) {
    final monthBuckets = <DateTime, Map<String, double>>{};
    final labelsByKey = <String, String>{};
    final totalByKey = <String, double>{};

    for (final month in _months) {
      monthBuckets[month] = <String, double>{};
    }

    for (final transaction in _filteredTransactions) {
      if (transaction.type != type) continue;

      final createdAt = transaction.createdAt;
      if (createdAt == null) continue;
      final month = DateTime(createdAt.year, createdAt.month, 1);
      if (!monthBuckets.containsKey(month)) continue;

      final key = transaction.categoryId.toString();
      labelsByKey.putIfAbsent(key, () => transaction.category);
      monthBuckets[month]![key] =
          (monthBuckets[month]![key] ?? 0) + transaction.amountRubles;
      totalByKey[key] = (totalByKey[key] ?? 0) + transaction.amountRubles;
    }

    final rankedKeys = totalByKey.keys.toList()
      ..sort((a, b) => (totalByKey[b] ?? 0).compareTo(totalByKey[a] ?? 0));

    final rows = _months.map((month) {
      final values = monthBuckets[month] ?? const <String, double>{};
      final segments = <_StackSegment>[];

      for (final key in rankedKeys) {
        final value = values[key] ?? 0;
        if (value > 0) {
          segments.add(
            _StackSegment(
              key: key,
              label: labelsByKey[key] ?? key,
              amount: value,
            ),
          );
        }
      }

      return _MonthlyStackedRow(month: month, segments: segments);
    }).toList();

    final legend = <_LegendEntry>[];
    final colorPalette = type == TransactionType.income
        ? _ChartPalette.income
        : _ChartPalette.expense;

    for (var i = 0; i < rankedKeys.length; i++) {
      final key = rankedKeys[i];
      legend.add(
        _LegendEntry(
          key: key,
          label: labelsByKey[key] ?? key,
          color: colorPalette[i % colorPalette.length],
        ),
      );
    }

    return _StackedChartData(rows: rows, legend: legend);
  }

  List<Category> get _incomeCategories {
    final categories = _categories
        .where((category) => category.type == CategoryType.income)
        .where((category) => _availableIncomeCategoryIds.contains(category.id))
        .toList();
    categories.sort(
      (a, b) => a.name.toLowerCase().compareTo(b.name.toLowerCase()),
    );
    return categories;
  }

  List<Category> get _expenseCategories {
    final categories = _categories
        .where((category) => category.type == CategoryType.expense)
        .where((category) => _availableExpenseCategoryIds.contains(category.id))
        .toList();
    categories.sort(
      (a, b) => a.name.toLowerCase().compareTo(b.name.toLowerCase()),
    );
    return categories;
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

class _StatsHeaderControls extends StatelessWidget {
  const _StatsHeaderControls({
    required this.groupByMonth,
    required this.onGroupByMonthChanged,
    required this.monthLabel,
    required this.startDateLabel,
    required this.endDateLabel,
    required this.startMonthLabel,
    required this.endMonthLabel,
    required this.isOnCurrentMonth,
    required this.onPreviousMonth,
    required this.onNextMonth,
    required this.onCurrentMonth,
    required this.onMonthTap,
    required this.onStartTap,
    required this.onEndTap,
    required this.onPickStartMonth,
    required this.onPickEndMonth,
  });

  final bool groupByMonth;
  final ValueChanged<bool> onGroupByMonthChanged;
  final String monthLabel;
  final String startDateLabel;
  final String endDateLabel;
  final String startMonthLabel;
  final String endMonthLabel;
  final bool isOnCurrentMonth;
  final VoidCallback onPreviousMonth;
  final VoidCallback onNextMonth;
  final VoidCallback onCurrentMonth;
  final VoidCallback onMonthTap;
  final VoidCallback onStartTap;
  final VoidCallback onEndTap;
  final VoidCallback onPickStartMonth;
  final VoidCallback onPickEndMonth;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppTheme.space12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(
                  "View",
                  style: textTheme.labelMedium?.copyWith(
                    color: colorScheme.onSurfaceVariant,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(width: AppTheme.space8),
                Expanded(
                  child: Align(
                    alignment: Alignment.centerRight,
                    child: SegmentedButton<bool>(
                      showSelectedIcon: false,
                      style: const ButtonStyle(
                        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                        visualDensity: VisualDensity.compact,
                      ),
                      segments: const [
                        ButtonSegment<bool>(
                          value: false,
                          icon: Icon(Icons.calendar_view_month_rounded),
                          label: Text("Month"),
                        ),
                        ButtonSegment<bool>(
                          value: true,
                          icon: Icon(Icons.stacked_line_chart_rounded),
                          label: Text("Range"),
                        ),
                      ],
                      selected: {groupByMonth},
                      onSelectionChanged: (selection) {
                        if (selection.isEmpty) return;
                        onGroupByMonthChanged(selection.first);
                      },
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppTheme.space8),
            if (groupByMonth)
              Row(
                children: [
                  Expanded(
                    child: _HeaderActionChip(
                      icon: Icons.calendar_month_rounded,
                      label: "From: $startMonthLabel",
                      onTap: onPickStartMonth,
                      expand: true,
                    ),
                  ),
                  const SizedBox(width: AppTheme.space8),
                  Icon(
                    Icons.arrow_forward_rounded,
                    size: AppTheme.iconSizeMedium,
                    color: colorScheme.onSurfaceVariant,
                  ),
                  const SizedBox(width: AppTheme.space8),
                  Expanded(
                    child: _HeaderActionChip(
                      icon: Icons.calendar_month_rounded,
                      label: "To: $endMonthLabel",
                      onTap: onPickEndMonth,
                      expand: true,
                    ),
                  ),
                ],
              )
            else
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Wrap(
                    spacing: AppTheme.space4,
                    runSpacing: AppTheme.space4,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      IconButton(
                        onPressed: onPreviousMonth,
                        tooltip: "Previous month",
                        visualDensity: VisualDensity.compact,
                        constraints: const BoxConstraints.tightFor(
                          width: 32,
                          height: 32,
                        ),
                        icon: const Icon(Icons.chevron_left_rounded),
                      ),
                      _HeaderActionChip(
                        icon: Icons.calendar_month_rounded,
                        label: monthLabel,
                        onTap: onMonthTap,
                      ),
                      IconButton(
                        onPressed: isOnCurrentMonth ? null : onNextMonth,
                        tooltip: "Next month",
                        visualDensity: VisualDensity.compact,
                        constraints: const BoxConstraints.tightFor(
                          width: 32,
                          height: 32,
                        ),
                        icon: const Icon(Icons.chevron_right_rounded),
                      ),
                      IconButton(
                        onPressed: isOnCurrentMonth ? null : onCurrentMonth,
                        tooltip: "Current month",
                        visualDensity: VisualDensity.compact,
                        constraints: const BoxConstraints.tightFor(
                          width: 32,
                          height: 32,
                        ),
                        icon: const Icon(Icons.today_rounded),
                      ),
                    ],
                  ),
                  const SizedBox(height: AppTheme.space8),
                  Row(
                    children: [
                      Expanded(
                        child: _HeaderActionChip(
                          label: "From: $startDateLabel",
                          onTap: onStartTap,
                          expand: true,
                        ),
                      ),
                      const SizedBox(width: AppTheme.space8),
                      Expanded(
                        child: _HeaderActionChip(
                          label: "To: $endDateLabel",
                          onTap: onEndTap,
                          expand: true,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
          ],
        ),
      ),
    );
  }
}

class _HeaderActionChip extends StatelessWidget {
  const _HeaderActionChip({
    required this.label,
    required this.onTap,
    this.icon,
    this.expand = false,
  });

  final String label;
  final VoidCallback onTap;
  final IconData? icon;
  final bool expand;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;

    return InkWell(
      onTap: onTap,
      borderRadius: AppTheme.borderRadiusSmall,
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: AppTheme.space8,
          vertical: AppTheme.space8,
        ),
        decoration: BoxDecoration(
          color: colorScheme.surfaceContainerLowest,
          borderRadius: AppTheme.borderRadiusSmall,
          border: Border.all(color: colorScheme.outlineVariant),
        ),
        width: expand ? double.infinity : null,
        child: Row(
          mainAxisSize: expand ? MainAxisSize.max : MainAxisSize.min,
          children: [
            if (icon != null) ...[
              Icon(icon, size: AppTheme.iconSizeSmall),
              const SizedBox(width: AppTheme.space4),
            ],
            Flexible(
              child: Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: textTheme.labelMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _MonthPoint {
  const _MonthPoint({
    required this.month,
    required this.income,
    required this.expense,
  });

  final DateTime month;
  final double income;
  final double expense;

  double get net => income - expense;
}

class _StackSegment {
  const _StackSegment({
    required this.key,
    required this.label,
    required this.amount,
  });

  final String key;
  final String label;
  final double amount;
}

class _MonthlyStackedRow {
  const _MonthlyStackedRow({required this.month, required this.segments});

  final DateTime month;
  final List<_StackSegment> segments;

  double get total =>
      segments.fold<double>(0, (sum, segment) => sum + segment.amount);
}

class _LegendEntry {
  const _LegendEntry({
    required this.key,
    required this.label,
    required this.color,
  });

  final String key;
  final String label;
  final Color color;
}

class _StackedChartData {
  const _StackedChartData({required this.rows, required this.legend});

  final List<_MonthlyStackedRow> rows;
  final List<_LegendEntry> legend;
}

class _MonthTrendCard extends StatelessWidget {
  const _MonthTrendCard({required this.points});

  final List<_MonthPoint> points;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final colorScheme = Theme.of(context).colorScheme;

    return Card(
      child: Padding(
        padding: AppTheme.cardPadding,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              "Net, income and expenses by month",
              style: textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: AppTheme.space12),
            SizedBox(
              height: 260,
              child: LineChart(
                LineChartData(
                  minY: _minY(points),
                  maxY: _maxY(points),
                  minX: 0,
                  maxX: (points.length - 1).toDouble(),
                  gridData: FlGridData(
                    show: true,
                    horizontalInterval: _gridInterval(points),
                    drawVerticalLine: false,
                    getDrawingHorizontalLine: (value) => FlLine(
                      color: colorScheme.outlineVariant.withAlpha(120),
                      strokeWidth: 1,
                    ),
                  ),
                  borderData: FlBorderData(
                    show: true,
                    border: Border(
                      left: BorderSide(color: colorScheme.outlineVariant),
                      bottom: BorderSide(color: colorScheme.outlineVariant),
                    ),
                  ),
                  lineTouchData: LineTouchData(
                    enabled: true,
                    touchTooltipData: LineTouchTooltipData(
                      getTooltipColor: (_) =>
                          _ChartTooltipStyle.backgroundColor,
                      getTooltipItems: (touchedSpots) {
                        return touchedSpots.map((spot) {
                          final label = switch (spot.barIndex) {
                            0 => "Income",
                            1 => "Expenses",
                            2 => "Net",
                            _ => "Value",
                          };
                          return LineTooltipItem(
                            "$label: ${formatAmount(spot.y)} ₽",
                            textTheme.labelMedium?.copyWith(
                                  color: Colors.white,
                                ) ??
                                const TextStyle(color: Colors.white),
                          );
                        }).toList();
                      },
                    ),
                  ),
                  titlesData: FlTitlesData(
                    topTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false),
                    ),
                    rightTitles: const AxisTitles(
                      sideTitles: SideTitles(showTitles: false),
                    ),
                    leftTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        reservedSize: 48,
                        interval: _gridInterval(points),
                        getTitlesWidget: (value, meta) =>
                            Text(_compact(value), style: textTheme.labelSmall),
                      ),
                    ),
                    bottomTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        interval: 1,
                        getTitlesWidget: (value, meta) {
                          final index = value.round();
                          if (index < 0 || index >= points.length) {
                            return const SizedBox.shrink();
                          }
                          return Padding(
                            padding: const EdgeInsets.only(
                              top: AppTheme.space8,
                            ),
                            child: Text(
                              _shortMonth(points[index].month),
                              style: textTheme.labelSmall,
                            ),
                          );
                        },
                      ),
                    ),
                  ),
                  lineBarsData: [
                    _line(points, (item) => item.income, AppTheme.incomeColor),
                    _line(
                      points,
                      (item) => item.expense,
                      AppTheme.expenseColor,
                    ),
                    _line(points, (item) => item.net, colorScheme.primary),
                  ],
                ),
              ),
            ),
            const SizedBox(height: AppTheme.space12),
            _LegendWrap(
              entries: [
                _LegendEntry(
                  key: "income",
                  label: "Income",
                  color: AppTheme.incomeColor,
                ),
                _LegendEntry(
                  key: "expense",
                  label: "Expenses",
                  color: AppTheme.expenseColor,
                ),
                _LegendEntry(
                  key: "net",
                  label: "Net",
                  color: colorScheme.primary,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  static String _shortMonth(DateTime date) {
    const months = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"];
    return months[date.month - 1];
  }

  static String _compact(double value) {
    final absolute = value.abs();
    if (absolute >= 1000000) {
      return "${(value / 1000000).toStringAsFixed(1)}M";
    }
    if (absolute >= 1000) {
      return "${(value / 1000).toStringAsFixed(0)}k";
    }
    return value.toStringAsFixed(0);
  }

  static double _gridInterval(List<_MonthPoint> points) {
    final span = (_maxY(points) - _minY(points)).abs();
    if (span <= 0) return 1;
    return (span / 4).clamp(1, double.infinity);
  }

  static LineChartBarData _line(
    List<_MonthPoint> points,
    double Function(_MonthPoint point) valueOf,
    Color color,
  ) {
    return LineChartBarData(
      spots: points
          .asMap()
          .entries
          .map((entry) => FlSpot(entry.key.toDouble(), valueOf(entry.value)))
          .toList(),
      isCurved: true,
      color: color,
      barWidth: 2,
      belowBarData: BarAreaData(show: false),
      dotData: FlDotData(show: false),
    );
  }

  static double _maxY(List<_MonthPoint> points) {
    final maxValue = points.fold<double>(0, (max, point) {
      final local = [
        point.expense,
        point.income,
        point.net,
      ].reduce((a, b) => a > b ? a : b);
      return local > max ? local : max;
    });
    if (maxValue <= 0) return 1;
    return maxValue * 1.2;
  }

  static double _minY(List<_MonthPoint> points) {
    final minValue = points.fold<double>(0, (min, point) {
      final local = [
        point.expense,
        point.income,
        point.net,
      ].reduce((a, b) => a < b ? a : b);
      return local < min ? local : min;
    });
    if (minValue >= 0) return 0;
    return minValue * 1.2;
  }
}

class _StackedMonthlyBarCard extends StatelessWidget {
  const _StackedMonthlyBarCard({
    required this.title,
    required this.rows,
    required this.legend,
    required this.emptyLabel,
  });

  final String title;
  final List<_MonthlyStackedRow> rows;
  final List<_LegendEntry> legend;
  final String emptyLabel;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final maxTotal = rows.fold<double>(
      0,
      (max, row) => row.total > max ? row.total : max,
    );
    final hasData = maxTotal > 0;
    final colorByKey = {for (final item in legend) item.key: item.color};

    return Card(
      child: Padding(
        padding: AppTheme.cardPadding,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: AppTheme.space12),
            if (!hasData)
              Text(
                emptyLabel,
                style: textTheme.bodySmall?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              )
            else
              SizedBox(
                height: 300,
                child: BarChart(
                  BarChartData(
                    minY: 0,
                    maxY: maxTotal * 1.2,
                    gridData: FlGridData(
                      show: true,
                      drawVerticalLine: false,
                      horizontalInterval: (maxTotal / 4).clamp(
                        1,
                        double.infinity,
                      ),
                      getDrawingHorizontalLine: (value) => FlLine(
                        color: Theme.of(
                          context,
                        ).colorScheme.outlineVariant.withAlpha(120),
                        strokeWidth: 1,
                      ),
                    ),
                    borderData: FlBorderData(
                      show: true,
                      border: Border(
                        left: BorderSide(
                          color: Theme.of(context).colorScheme.outlineVariant,
                        ),
                        bottom: BorderSide(
                          color: Theme.of(context).colorScheme.outlineVariant,
                        ),
                      ),
                    ),
                    titlesData: FlTitlesData(
                      topTitles: const AxisTitles(
                        sideTitles: SideTitles(showTitles: false),
                      ),
                      rightTitles: const AxisTitles(
                        sideTitles: SideTitles(showTitles: false),
                      ),
                      leftTitles: AxisTitles(
                        sideTitles: SideTitles(
                          showTitles: true,
                          reservedSize: 48,
                          getTitlesWidget: (value, meta) => Text(
                            _MonthTrendCard._compact(value),
                            style: textTheme.labelSmall,
                          ),
                        ),
                      ),
                      bottomTitles: AxisTitles(
                        sideTitles: SideTitles(
                          showTitles: true,
                          reservedSize: 38,
                          interval: 1,
                          getTitlesWidget: (value, meta) {
                            final index = value.round();
                            if (index < 0 || index >= rows.length) {
                              return const SizedBox.shrink();
                            }
                            final month = rows[index].month;
                            return Padding(
                              padding: const EdgeInsets.only(
                                top: AppTheme.space8,
                              ),
                              child: Text(
                                "${_MonthTrendCard._shortMonth(month)}\n${month.year % 100}",
                                textAlign: TextAlign.center,
                                style: textTheme.labelSmall,
                              ),
                            );
                          },
                        ),
                      ),
                    ),
                    barTouchData: BarTouchData(
                      enabled: true,
                      touchTooltipData: BarTouchTooltipData(
                        getTooltipColor: (_) =>
                            _ChartTooltipStyle.backgroundColor,
                        getTooltipItem: (group, groupIndex, rod, rodIndex) {
                          final row = rows[group.x.toInt()];
                          final monthTitle =
                              "${row.month.month.toString().padLeft(2, "0")}.${row.month.year}";
                          final visibleSegments = row.segments
                              .where((segment) => segment.amount > 0)
                              .toList();
                          return BarTooltipItem(
                            "$monthTitle\nTotal: ${formatAmount(row.total)} ₽",
                            textTheme.labelMedium?.copyWith(
                                  color: Colors.white,
                                ) ??
                                const TextStyle(color: Colors.white),
                            children: visibleSegments
                                .map(
                                  (segment) => TextSpan(
                                    text:
                                        "\n${segment.label}: ${formatAmount(segment.amount)} ₽",
                                  ),
                                )
                                .toList(),
                          );
                        },
                      ),
                    ),
                    barGroups: rows.asMap().entries.map((entry) {
                      final index = entry.key;
                      final row = entry.value;
                      var cursor = 0.0;
                      final stacks = <BarChartRodStackItem>[];
                      for (final segment in row.segments) {
                        final from = cursor;
                        final to = cursor + segment.amount;
                        final color =
                            colorByKey[segment.key] ?? const Color(0xFF90A4AE);
                        stacks.add(BarChartRodStackItem(from, to, color));
                        cursor = to;
                      }

                      return BarChartGroupData(
                        x: index,
                        barRods: [
                          BarChartRodData(
                            toY: row.total,
                            rodStackItems: stacks,
                            width: 18,
                            borderRadius: AppTheme.borderRadiusSmall,
                          ),
                        ],
                      );
                    }).toList(),
                  ),
                ),
              ),
            if (hasData) ...[
              const SizedBox(height: AppTheme.space12),
              _LegendWrap(entries: legend),
            ],
          ],
        ),
      ),
    );
  }
}

class _LegendWrap extends StatelessWidget {
  const _LegendWrap({required this.entries});

  final List<_LegendEntry> entries;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    return Wrap(
      spacing: AppTheme.space12,
      runSpacing: AppTheme.space8,
      children: entries
          .map(
            (entry) => Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 10,
                  height: 10,
                  decoration: BoxDecoration(
                    color: entry.color,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: AppTheme.space4),
                Text(entry.label, style: textTheme.labelMedium),
              ],
            ),
          )
          .toList(),
    );
  }
}

class _ChartPalette {
  static const List<Color> income = [
    Color(0xFF2E7D32),
    Color(0xFF00897B),
    Color(0xFF0097A7),
    Color(0xFF1976D2),
    Color(0xFF43A047),
    Color(0xFF26A69A),
  ];

  static const List<Color> expense = [
    Color(0xFFC62828),
    Color(0xFFD32F2F),
    Color(0xFFF4511E),
    Color(0xFFFF7043),
    Color(0xFF8E24AA),
    Color(0xFFEC407A),
  ];
}

class _ChartTooltipStyle {
  static const Color backgroundColor = Color(0xCC1F2937);
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

class _PieChartCard extends StatefulWidget {
  const _PieChartCard({
    required this.baseColor,
    required this.palette,
    required this.data,
    required this.emptyLabel,
  });

  static const double _minSlicePercent = 1;
  static const double _chartHeight = 220;
  static const double _minLegendHeight = 56;
  static const double _maxLegendHeight = 172;
  static const double _legendRowHeight = 30;

  final Color baseColor;
  final List<Color> palette;
  final List<_CategoryTotal> data;
  final String emptyLabel;

  @override
  State<_PieChartCard> createState() => _PieChartCardState();
}

class _PieChartCardState extends State<_PieChartCard> {
  int? _touchedSectionIndex;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final colorScheme = Theme.of(context).colorScheme;
    final sliceTotals = _buildSliceTotals(widget.data);
    final sections = _buildSections(sliceTotals);
    final legendHeight = _legendHeightForCount(widget.data.length);
    final touchedIndex = _touchedSectionIndex;
    final touchedItem =
        touchedIndex != null &&
            touchedIndex >= 0 &&
            touchedIndex < sliceTotals.length
        ? sliceTotals[touchedIndex]
        : null;

    return Card(
      child: Padding(
        padding: AppTheme.cardPadding,
        child: widget.data.isEmpty
            ? SizedBox(
                height: _PieChartCard._chartHeight,
                child: Center(
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
                        widget.emptyLabel,
                        style: textTheme.bodySmall?.copyWith(
                          color: colorScheme.onSurfaceVariant,
                        ),
                        textAlign: TextAlign.center,
                      ),
                    ],
                  ),
                ),
              )
            : Column(
                children: [
                  SizedBox(
                    height: _PieChartCard._chartHeight,
                    child: Stack(
                      children: [
                        PieChart(
                          PieChartData(
                            sections: sections,
                            centerSpaceRadius: 52,
                            sectionsSpace: 2,
                            pieTouchData: PieTouchData(
                              enabled: true,
                              touchCallback: (event, response) {
                                final touchedSection = response?.touchedSection;
                                if (!event.isInterestedForInteractions ||
                                    touchedSection == null) {
                                  if (_touchedSectionIndex != null) {
                                    setState(() {
                                      _touchedSectionIndex = null;
                                    });
                                  }
                                  return;
                                }

                                final index =
                                    touchedSection.touchedSectionIndex;
                                if (index < 0 || index >= sliceTotals.length) {
                                  if (_touchedSectionIndex != null) {
                                    setState(() {
                                      _touchedSectionIndex = null;
                                    });
                                  }
                                  return;
                                }
                                if (_touchedSectionIndex != index) {
                                  setState(() {
                                    _touchedSectionIndex = index;
                                  });
                                }
                              },
                            ),
                          ),
                        ),
                        Positioned(
                          top: 0,
                          left: 0,
                          right: 0,
                          child: Center(
                            child: AnimatedSwitcher(
                              duration: const Duration(milliseconds: 120),
                              child: touchedItem == null
                                  ? const SizedBox.shrink()
                                  : _PieTouchTooltip(
                                      key: ValueKey<int>(
                                        touchedItem.categoryId,
                                      ),
                                      label: touchedItem.name,
                                      value:
                                          "${formatAmount(touchedItem.total)} ₽",
                                    ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: AppTheme.space16),
                  AnimatedSize(
                    duration: const Duration(milliseconds: 180),
                    curve: Curves.easeOut,
                    alignment: Alignment.topCenter,
                    child: SizedBox(
                      height: legendHeight,
                      child: Scrollbar(
                        child: SingleChildScrollView(
                          child: Column(
                            children: widget.data
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
                  ),
                ],
              ),
      ),
    );
  }

  double _legendHeightForCount(int count) {
    if (count <= 0) return _PieChartCard._minLegendHeight;
    final desired = count * _PieChartCard._legendRowHeight;
    return desired
        .clamp(_PieChartCard._minLegendHeight, _PieChartCard._maxLegendHeight)
        .toDouble();
  }

  List<_CategoryTotal> _buildSliceTotals(List<_CategoryTotal> totals) {
    final totalValue = totals.fold<double>(0, (sum, item) => sum + item.total);
    if (totalValue == 0) return <_CategoryTotal>[];

    final colors = totals.length > 1 ? widget.palette : [widget.baseColor];
    final visibleTotals = totals
        .where(
          (item) =>
              item.total / totalValue * 100 >= _PieChartCard._minSlicePercent,
        )
        .toList();
    final sliceTotals = visibleTotals.isEmpty ? totals : visibleTotals;

    for (var i = 0; i < sliceTotals.length; i++) {
      sliceTotals[i].color = colors[i % colors.length];
    }

    return sliceTotals;
  }

  List<PieChartSectionData> _buildSections(List<_CategoryTotal> sliceTotals) {
    final totalValue = sliceTotals.fold<double>(
      0,
      (sum, item) => sum + item.total,
    );
    if (totalValue == 0) return [];

    return sliceTotals.asMap().entries.map((entry) {
      final item = entry.value;
      final value = item.total;
      final percentage = value / totalValue * 100;
      return PieChartSectionData(
        color: item.color,
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

class _PieTouchTooltip extends StatelessWidget {
  const _PieTouchTooltip({super.key, required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppTheme.space8,
        vertical: AppTheme.space4,
      ),
      decoration: BoxDecoration(
        color: _ChartTooltipStyle.backgroundColor,
        borderRadius: AppTheme.borderRadiusSmall,
      ),
      child: Text(
        "$label\n$value",
        textAlign: TextAlign.center,
        style:
            textTheme.labelMedium?.copyWith(color: Colors.white) ??
            const TextStyle(color: Colors.white),
      ),
    );
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
    return formatDayMonthYearLabel(date);
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
