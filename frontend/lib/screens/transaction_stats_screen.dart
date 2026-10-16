import 'package:flutter/material.dart';

import 'package:fl_chart/fl_chart.dart';

import 'package:expenis_mobile/models/category.dart';
import 'package:expenis_mobile/models/tag_period.dart';
import 'package:expenis_mobile/models/transaction.dart';
import 'package:expenis_mobile/screens/edit_transaction_screen.dart';
import 'package:expenis_mobile/service/category_service.dart';
import 'package:expenis_mobile/service/transaction_service.dart';
import 'package:expenis_mobile/theme.dart';
import 'package:expenis_mobile/utils/chart_utils.dart';
import 'package:expenis_mobile/utils/date_labels.dart';
import 'package:expenis_mobile/utils/format.dart';
import 'package:expenis_mobile/utils/selection_utils.dart';
import 'package:expenis_mobile/utils/tag_utils.dart';
import 'package:expenis_mobile/widgets/analytics_filters_card.dart';
import 'package:expenis_mobile/widgets/app_empty_state.dart';
import 'package:expenis_mobile/widgets/app_error_state.dart';
import 'package:expenis_mobile/widgets/month_picker_bottom_sheet.dart';
import 'package:expenis_mobile/widgets/responsive.dart';

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
  // null = all categories, including ones that appear in later periods.
  Set<int>? _explicitIncomeCategoryIds;
  Set<int>? _explicitExpenseCategoryIds;
  List<TagPeriod> _tagPeriods = [];
  bool _hasLoadedTagPeriods = false;
  Map<String, String> _availableIncomeTagsByNormalized = {};
  Map<String, String> _availableExpenseTagsByNormalized = {};
  Set<String> _includedIncomeTagKeys = {};
  Set<String> _excludedIncomeTagKeys = {};
  Set<String> _includedExpenseTagKeys = {};
  Set<String> _excludedExpenseTagKeys = {};
  bool _isFirstLoad = true;
  bool _isLoading = false;
  bool _groupByMonth = false;
  TransactionType _selectedType = TransactionType.expense;
  String? _loadError;

  bool get _isIncomeSelected => _selectedType == TransactionType.income;

  Set<int> get _selectedIncomeCategoryIds => effectiveSelection(
    _explicitIncomeCategoryIds,
    _availableIncomeCategoryIds,
  );

  Set<int> get _selectedExpenseCategoryIds => effectiveSelection(
    _explicitExpenseCategoryIds,
    _availableExpenseCategoryIds,
  );

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
        _hasLoadedTagPeriods
            ? Future.value(_tagPeriods)
            : _transactionService.fetchTagPeriods(),
      ]);

      if (!mounted) return;
      final transactions = results[0] as List<Transaction>;
      final categories = results[1] as List<Category>;
      final tagPeriods = results[2] as List<TagPeriod>;
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
        _availableIncomeTagsByNormalized = incomeTagsByNormalized;
        _availableExpenseTagsByNormalized = expenseTagsByNormalized;
        _tagPeriods = tagPeriods;
        _hasLoadedTagPeriods = true;
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
    _loadData();
  }

  void _toggleIncomeCategory(int id) {
    setState(() {
      _explicitIncomeCategoryIds = toggledExplicitSelection(
        _explicitIncomeCategoryIds,
        _availableIncomeCategoryIds,
        id,
      );
    });
  }

  void _toggleExpenseCategory(int id) {
    setState(() {
      _explicitExpenseCategoryIds = toggledExplicitSelection(
        _explicitExpenseCategoryIds,
        _availableExpenseCategoryIds,
        id,
      );
    });
  }

  void _setIncomeCategorySelection(Set<int>? explicitIds) {
    setState(() {
      _explicitIncomeCategoryIds = explicitIds;
    });
  }

  void _setExpenseCategorySelection(Set<int>? explicitIds) {
    setState(() {
      _explicitExpenseCategoryIds = explicitIds;
    });
  }

  void _cycleIncomeTag(String tagKey) {
    setState(() {
      final next = cycleTagFilter(
        _includedIncomeTagKeys,
        _excludedIncomeTagKeys,
        tagKey,
      );
      _includedIncomeTagKeys = next.included;
      _excludedIncomeTagKeys = next.excluded;
    });
  }

  void _cycleExpenseTag(String tagKey) {
    setState(() {
      final next = cycleTagFilter(
        _includedExpenseTagKeys,
        _excludedExpenseTagKeys,
        tagKey,
      );
      _includedExpenseTagKeys = next.included;
      _excludedExpenseTagKeys = next.excluded;
    });
  }

  void _setIncomeTagSelection(
    Set<String> includedKeys,
    Set<String> excludedKeys,
  ) {
    setState(() {
      _includedIncomeTagKeys = includedKeys;
      _excludedIncomeTagKeys = excludedKeys;
    });
  }

  void _setExpenseTagSelection(
    Set<String> includedKeys,
    Set<String> excludedKeys,
  ) {
    setState(() {
      _includedExpenseTagKeys = includedKeys;
      _excludedExpenseTagKeys = excludedKeys;
    });
  }

  List<TagPeriod> _tagPeriodsOf(TransactionType type) {
    return _tagPeriods.where((period) => period.type == type).toList();
  }

  /// Tags used on [type] at some point but absent from the loaded period.
  Map<String, String> _outOfPeriodTags(
    TransactionType type,
    Map<String, String> inPeriodTags,
  ) {
    final result = <String, String>{};
    for (final period in _tagPeriodsOf(type)) {
      final key = normalizeTagKey(period.name);
      if (key.isEmpty || inPeriodTags.containsKey(key)) continue;
      result.putIfAbsent(key, () => period.name.trim());
    }
    return result;
  }

  Set<String> get _selectedIncludedTagKeys =>
      _isIncomeSelected ? _includedIncomeTagKeys : _includedExpenseTagKeys;

  /// Combined period of the included tags when it does not fit the range.
  ({DateTime firstMonth, DateTime lastMonth})? get _tagPeriodOutsideRange {
    final period = combinedTagPeriod(
      _selectedIncludedTagKeys,
      _tagPeriodsOf(_selectedType),
    );
    if (period == null) return null;
    final fits =
        !period.firstMonth.isBefore(_startMonth) &&
        !period.lastMonth.isAfter(_endMonth);
    return fits ? null : period;
  }

  void _showTagPeriod(DateTime firstMonth, DateTime lastMonth) {
    final now = DateTime.now();
    final currentMonth = DateTime(now.year, now.month, 1);
    final endMonth = lastMonth.isAfter(currentMonth) ? currentMonth : lastMonth;

    if (!firstMonth.isBefore(endMonth)) {
      setState(() => _groupByMonth = false);
      _applyMonthRange(firstMonth);
      return;
    }

    setState(() {
      _groupByMonth = true;
      _startDate = firstMonth;
      final endDate = _isCurrentMonth(endMonth)
          ? now
          : _lastDayOfMonth(endMonth);
      _endDate = DateTime(endDate.year, endDate.month, endDate.day);
      _rebuildMonths();
    });
    _loadData();
  }

  Widget? _buildTagPeriodHint() {
    final period = _tagPeriodOutsideRange;
    if (period == null) return null;

    final inPeriodLabels = _isIncomeSelected
        ? _availableIncomeTagsByNormalized
        : _availableExpenseTagsByNormalized;
    final outOfPeriodLabels = _outOfPeriodTags(_selectedType, inPeriodLabels);
    final tagKeys = _selectedIncludedTagKeys.toList()..sort();
    final tagNames = tagKeys
        .map((key) => inPeriodLabels[key] ?? outOfPeriodLabels[key] ?? key)
        .join(", ");
    final firstLabel = formatMonthYearLabel(period.firstMonth);
    final lastLabel = formatMonthYearLabel(period.lastMonth);
    final periodLabel = firstLabel == lastLabel
        ? firstLabel
        : "$firstLabel – $lastLabel";

    return _TagPeriodHint(
      message: "$tagNames: transactions in $periodLabel",
      onShowPeriod: () => _showTagPeriod(period.firstMonth, period.lastMonth),
    );
  }

  bool _transactionMatchesTagFilter(Transaction transaction) {
    final isIncome = transaction.type == TransactionType.income;
    return matchesTagFilter(
      transaction.tags,
      includedKeys: isIncome ? _includedIncomeTagKeys : _includedExpenseTagKeys,
      excludedKeys: isIncome ? _excludedIncomeTagKeys : _excludedExpenseTagKeys,
    );
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
      // The edit may have changed tags or dates.
      _hasLoadedTagPeriods = false;
      _loadData();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Statistics")),
      body: SafeArea(
        top: false,
        bottom: true,
        child: ResponsiveCenter(
          maxWidth: Breakpoints.dashboardMaxWidth,
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

  /// Narrow screens get a single scrolling column. Wide screens put the
  /// charts on the left and the drill-down (filters, transactions) on the
  /// right, each scrolling independently.
  Widget _buildResponsiveBody({
    required List<Widget> primary,
    required List<Widget> secondary,
  }) {
    return LayoutBuilder(
      builder: (context, constraints) {
        if (constraints.maxWidth < Breakpoints.twoColumnMinWidth) {
          return ListView(
            padding: AppTheme.screenPadding,
            children: _withSpacing([...primary, ...secondary]),
          );
        }

        return Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              flex: 3,
              child: ListView(
                padding: const EdgeInsets.fromLTRB(
                  AppTheme.space16,
                  AppTheme.space16,
                  AppTheme.space8,
                  AppTheme.space16,
                ),
                children: _withSpacing(primary),
              ),
            ),
            Expanded(
              flex: 2,
              child: ListView(
                padding: const EdgeInsets.fromLTRB(
                  AppTheme.space8,
                  AppTheme.space16,
                  AppTheme.space16,
                  AppTheme.space16,
                ),
                children: _withSpacing(secondary),
              ),
            ),
          ],
        );
      },
    );
  }

  static List<Widget> _withSpacing(List<Widget> children) {
    return [
      for (var i = 0; i < children.length; i++) ...[
        if (i > 0) const SizedBox(height: AppTheme.space16),
        children[i],
      ],
    ];
  }

  Widget _buildTypeSelector() {
    return SegmentedButton<TransactionType>(
      expandedInsets: EdgeInsets.zero,
      showSelectedIcon: false,
      segments: const [
        ButtonSegment(
          value: TransactionType.income,
          icon: Icon(Icons.arrow_downward_rounded),
          label: Text("Income"),
        ),
        ButtonSegment(
          value: TransactionType.expense,
          icon: Icon(Icons.arrow_upward_rounded),
          label: Text("Expenses"),
        ),
      ],
      selected: {_selectedType},
      onSelectionChanged: (selection) {
        setState(() => _selectedType = selection.first);
      },
    );
  }

  Widget _buildFiltersCard() {
    final isIncome = _isIncomeSelected;
    return AnalyticsFiltersCard(
      title: isIncome ? "Income filters" : "Expense filters",
      accentColor: isIncome ? AppTheme.incomeColor : AppTheme.expenseColor,
      categories: isIncome ? _incomeCategories : _expenseCategories,
      selectedCategoryIds: isIncome
          ? _selectedIncomeCategoryIds
          : _selectedExpenseCategoryIds,
      onToggleCategory: isIncome
          ? _toggleIncomeCategory
          : _toggleExpenseCategory,
      onSelectAllCategories: () => isIncome
          ? _setIncomeCategorySelection(null)
          : _setExpenseCategorySelection(null),
      onClearAllCategories: () => isIncome
          ? _setIncomeCategorySelection(<int>{})
          : _setExpenseCategorySelection(<int>{}),
      tagLabelsByKey: isIncome
          ? _availableIncomeTagsByNormalized
          : _availableExpenseTagsByNormalized,
      outOfPeriodTagLabelsByKey: _outOfPeriodTags(
        _selectedType,
        isIncome
            ? _availableIncomeTagsByNormalized
            : _availableExpenseTagsByNormalized,
      ),
      includedTagKeys: isIncome
          ? _includedIncomeTagKeys
          : _includedExpenseTagKeys,
      excludedTagKeys: isIncome
          ? _excludedIncomeTagKeys
          : _excludedExpenseTagKeys,
      onCycleTag: isIncome ? _cycleIncomeTag : _cycleExpenseTag,
      onSetTagSelection: isIncome
          ? _setIncomeTagSelection
          : _setExpenseTagSelection,
    );
  }

  Widget _buildCategorySection(List<Transaction> transactions) {
    final isIncome = _isIncomeSelected;
    return _CategorySection(
      // Resets the touched slice when switching between income and expenses.
      key: ValueKey<TransactionType>(_selectedType),
      title: isIncome ? "Income by category" : "Expenses by category",
      color: isIncome ? AppTheme.incomeColor : AppTheme.expenseColor,
      icon: isIncome
          ? Icons.arrow_downward_rounded
          : Icons.arrow_upward_rounded,
      chartData: _buildCategoryTotals(transactions),
      emptyLabel: isIncome
          ? "No income matches the selected filters"
          : "No expenses match the selected filters",
    );
  }

  Widget _buildDetailedContent() {
    // With known tags the filters stay reachable, so an earlier tag can be picked.
    if (_transactions.isEmpty && _tagPeriods.isEmpty) {
      return const AppEmptyState(
        icon: Icons.pie_chart_outline_rounded,
        title: "No transactions",
        subtitle: "There are no transactions in this range",
      );
    }

    final income = _transactions
        .where((t) => t.type == TransactionType.income)
        .where((t) => _selectedIncomeCategoryIds.contains(t.categoryId))
        .where(_transactionMatchesTagFilter)
        .toList();
    final expense = _transactions
        .where((t) => t.type == TransactionType.expense)
        .where((t) => _selectedExpenseCategoryIds.contains(t.categoryId))
        .where(_transactionMatchesTagFilter)
        .toList();

    final incomeTotal = income.fold<double>(0, (s, t) => s + t.amountRubles);
    final expenseTotal = expense.fold<double>(0, (s, t) => s + t.amountRubles);
    final net = incomeTotal - expenseTotal;

    final isIncome = _isIncomeSelected;
    final selected = isIncome ? income : expense;

    return _buildResponsiveBody(
      primary: [
        _TotalSummaryCard(
          incomeTotal: incomeTotal,
          expenseTotal: expenseTotal,
          netTotal: net,
        ),
        _buildTypeSelector(),
        _buildCategorySection(selected),
      ],
      secondary: [
        _buildFiltersCard(),
        // Below the card so its appearance doesn't shift (and collapse) the card.
        ?_buildTagPeriodHint(),
        _TransactionsSection(
          title: isIncome ? "Income transactions" : "Expense transactions",
          color: isIncome ? AppTheme.incomeColor : AppTheme.expenseColor,
          icon: isIncome
              ? Icons.arrow_downward_rounded
              : Icons.arrow_upward_rounded,
          transactions: selected,
          onTap: _openEdit,
        ),
      ],
    );
  }

  Widget _buildGroupedContent() {
    final filtered = _filteredTransactions;
    final monthPoints = _buildMonthPoints(filtered);
    final stacked = _buildStackedMonthlyData(filtered, _selectedType);
    final isIncome = _isIncomeSelected;

    return _buildResponsiveBody(
      primary: [
        _MonthTrendCard(points: monthPoints),
        _buildTypeSelector(),
        _StackedMonthlyBarCard(
          title: isIncome ? "Income by category" : "Expenses by category",
          rows: stacked.rows,
          legend: stacked.legend,
          emptyLabel: isIncome
              ? "No income in selected range"
              : "No expenses in selected range",
        ),
      ],
      secondary: [
        _buildCategorySection(
          filtered.where((t) => t.type == _selectedType).toList(),
        ),
        _buildFiltersCard(),
        // Below the card so its appearance doesn't shift (and collapse) the card.
        ?_buildTagPeriodHint(),
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

    return _transactionMatchesTagFilter(transaction);
  }

  List<Transaction> get _filteredTransactions {
    return _transactions.where(_matchesFilters).toList();
  }

  List<_MonthPoint> _buildMonthPoints(List<Transaction> filtered) {
    return _months.map((month) {
      double income = 0;
      double expense = 0;
      for (final transaction in filtered) {
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

  _StackedChartData _buildStackedMonthlyData(
    List<Transaction> filtered,
    TransactionType type,
  ) {
    const otherKey = "other";
    final monthBuckets = <DateTime, Map<String, double>>{};
    final labelsByKey = <String, String>{};
    final totalByKey = <String, double>{};

    for (final month in _months) {
      monthBuckets[month] = <String, double>{};
    }

    for (final transaction in filtered) {
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

    // Small categories are merged into "Other" so every colour stays unique.
    // One palette slot is held back: a lone leftover key keeps its own colour.
    final topKeys = topKeysByTotal(
      totalByKey,
      AppTheme.chartPalette.length - 1,
    );
    final topKeySet = topKeys.toSet();
    final hasOther = topKeys.length < totalByKey.length;

    final rows = _months.map((month) {
      final values = monthBuckets[month] ?? const <String, double>{};
      final segments = <_StackSegment>[];

      for (final key in topKeys) {
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

      if (hasOther) {
        final otherAmount = values.entries
            .where((entry) => !topKeySet.contains(entry.key))
            .fold<double>(0, (sum, entry) => sum + entry.value);
        if (otherAmount > 0) {
          segments.add(
            _StackSegment(key: otherKey, label: "Other", amount: otherAmount),
          );
        }
      }

      return _MonthlyStackedRow(month: month, segments: segments);
    }).toList();

    final legend = <_LegendEntry>[
      for (var i = 0; i < topKeys.length; i++)
        _LegendEntry(
          key: topKeys[i],
          label: labelsByKey[topKeys[i]] ?? topKeys[i],
          color: AppTheme.chartPalette[i],
        ),
      if (hasOther)
        const _LegendEntry(
          key: otherKey,
          label: "Other",
          color: AppTheme.chartOtherColor,
        ),
    ];

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

/// Width reserved for Y-axis labels such as "125k".
const double _yAxisReservedSize = 44;

/// Minimum horizontal room per X-axis month label before labels get skipped.
const double _monthLabelMinWidth = 36;

FlGridData _horizontalGrid(ColorScheme colorScheme, double interval) {
  return FlGridData(
    show: true,
    drawVerticalLine: false,
    horizontalInterval: interval,
    getDrawingHorizontalLine: (value) => FlLine(
      color: colorScheme.outlineVariant.withAlpha(120),
      strokeWidth: 1,
    ),
  );
}

FlBorderData _axisBorder(ColorScheme colorScheme) {
  return FlBorderData(
    show: true,
    border: Border(
      left: BorderSide(color: colorScheme.outlineVariant),
      bottom: BorderSide(color: colorScheme.outlineVariant),
    ),
  );
}

/// Amount ticks on the left and month names along the bottom. The year is
/// added under the first label and under every January.
FlTitlesData _monthAxisTitles({
  required List<DateTime> months,
  required AxisScale scale,
  required int labelStride,
  required TextTheme textTheme,
}) {
  return FlTitlesData(
    topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
    rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
    leftTitles: AxisTitles(
      sideTitles: SideTitles(
        showTitles: true,
        reservedSize: _yAxisReservedSize,
        interval: scale.step,
        getTitlesWidget: (value, meta) =>
            Text(compactAmount(value), style: textTheme.labelSmall),
      ),
    ),
    bottomTitles: AxisTitles(
      sideTitles: SideTitles(
        showTitles: true,
        reservedSize: 40,
        interval: 1,
        getTitlesWidget: (value, meta) {
          final index = value.round();
          if (index != value || index < 0 || index >= months.length) {
            return const SizedBox.shrink();
          }
          if (index % labelStride != 0) return const SizedBox.shrink();
          final month = months[index];
          final showYear = index == 0 || month.month == DateTime.january;
          return Padding(
            padding: const EdgeInsets.only(top: AppTheme.space4),
            child: Text(
              showYear
                  ? "${monthShortLabel(month.month)}\n${month.year}"
                  : monthShortLabel(month.month),
              textAlign: TextAlign.center,
              style: textTheme.labelSmall,
            ),
          );
        },
      ),
    ),
  );
}

class _MonthTrendCard extends StatelessWidget {
  const _MonthTrendCard({required this.points});

  /// Point markers clutter the line once there are more months than this.
  static const int _maxPointsWithDots = 24;

  final List<_MonthPoint> points;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final colorScheme = Theme.of(context).colorScheme;
    final scale = niceAxisScale(_minValue(points), _maxValue(points));
    final showDots = points.length <= _maxPointsWithDots;
    final tooltipStyle =
        textTheme.labelMedium?.copyWith(color: Colors.white) ??
        const TextStyle(color: Colors.white);

    return Card(
      child: Padding(
        padding: AppTheme.cardPadding,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              "Income, expenses and net by month",
              style: textTheme.titleSmall?.copyWith(
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: AppTheme.space16),
            SizedBox(
              height: 260,
              child: LayoutBuilder(
                builder: (context, constraints) {
                  final stride = labelStride(
                    points.length,
                    constraints.maxWidth - _yAxisReservedSize,
                    _monthLabelMinWidth,
                  );
                  return LineChart(
                    LineChartData(
                      minY: scale.min,
                      maxY: scale.max,
                      minX: 0,
                      maxX: points.length > 1 ? points.length - 1 : 1,
                      gridData: _horizontalGrid(colorScheme, scale.step),
                      borderData: _axisBorder(colorScheme),
                      extraLinesData: ExtraLinesData(
                        horizontalLines: [
                          if (scale.min < 0)
                            HorizontalLine(
                              y: 0,
                              color: colorScheme.outline,
                              strokeWidth: 1,
                            ),
                        ],
                      ),
                      lineTouchData: LineTouchData(
                        enabled: true,
                        touchTooltipData: LineTouchTooltipData(
                          getTooltipColor: (_) =>
                              _ChartTooltipStyle.backgroundColor,
                          fitInsideHorizontally: true,
                          fitInsideVertically: true,
                          getTooltipItems: (touchedSpots) {
                            return touchedSpots.asMap().entries.map((entry) {
                              final spot = entry.value;
                              final label = switch (spot.barIndex) {
                                0 => "Income",
                                1 => "Expenses",
                                2 => "Net",
                                _ => "Value",
                              };
                              final index = spot.x.round();
                              final header =
                                  entry.key == 0 &&
                                      index >= 0 &&
                                      index < points.length
                                  ? "${formatMonthYearLabel(points[index].month)}\n"
                                  : "";
                              return LineTooltipItem(
                                "$header$label: ${formatAmount(spot.y)} ₽",
                                tooltipStyle,
                                textAlign: TextAlign.start,
                              );
                            }).toList();
                          },
                        ),
                      ),
                      titlesData: _monthAxisTitles(
                        months: points.map((point) => point.month).toList(),
                        scale: scale,
                        labelStride: stride,
                        textTheme: textTheme,
                      ),
                      lineBarsData: [
                        _line(
                          points,
                          (item) => item.income,
                          AppTheme.incomeColor,
                          showDots: showDots,
                        ),
                        _line(
                          points,
                          (item) => item.expense,
                          AppTheme.expenseColor,
                          showDots: showDots,
                        ),
                        _line(
                          points,
                          (item) => item.net,
                          colorScheme.primary,
                          showDots: false,
                          dashed: true,
                        ),
                      ],
                    ),
                  );
                },
              ),
            ),
            const SizedBox(height: AppTheme.space12),
            _LegendWrap(
              entries: [
                const _LegendEntry(
                  key: "income",
                  label: "Income",
                  color: AppTheme.incomeColor,
                ),
                const _LegendEntry(
                  key: "expense",
                  label: "Expenses",
                  color: AppTheme.expenseColor,
                ),
                _LegendEntry(
                  key: "net",
                  label: "Net (dashed)",
                  color: colorScheme.primary,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  // Straight segments on purpose: a smoothed curve overshoots between months
  // and suggests values (even negative ones) that never happened.
  static LineChartBarData _line(
    List<_MonthPoint> points,
    double Function(_MonthPoint point) valueOf,
    Color color, {
    required bool showDots,
    bool dashed = false,
  }) {
    return LineChartBarData(
      spots: points
          .asMap()
          .entries
          .map((entry) => FlSpot(entry.key.toDouble(), valueOf(entry.value)))
          .toList(),
      isCurved: false,
      color: color,
      barWidth: dashed ? 2 : 2.5,
      dashArray: dashed ? const [6, 4] : null,
      belowBarData: BarAreaData(show: false),
      dotData: FlDotData(
        show: showDots,
        getDotPainter: (spot, percent, bar, index) =>
            FlDotCirclePainter(radius: 3, color: color, strokeWidth: 0),
      ),
    );
  }

  static double _maxValue(List<_MonthPoint> points) {
    return points.fold<double>(0, (max, point) {
      final local = [
        point.expense,
        point.income,
        point.net,
      ].reduce((a, b) => a > b ? a : b);
      return local > max ? local : max;
    });
  }

  static double _minValue(List<_MonthPoint> points) {
    return points.fold<double>(0, (min, point) {
      final local = [
        point.expense,
        point.income,
        point.net,
      ].reduce((a, b) => a < b ? a : b);
      return local < min ? local : min;
    });
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
    final colorScheme = Theme.of(context).colorScheme;
    final maxTotal = rows.fold<double>(
      0,
      (max, row) => row.total > max ? row.total : max,
    );
    final hasData = maxTotal > 0;
    final scale = niceAxisScale(0, maxTotal);
    final colorByKey = {for (final item in legend) item.key: item.color};
    final tooltipStyle =
        textTheme.labelMedium?.copyWith(color: Colors.white) ??
        const TextStyle(color: Colors.white);

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
            const SizedBox(height: AppTheme.space16),
            if (!hasData)
              Text(
                emptyLabel,
                style: textTheme.bodySmall?.copyWith(
                  color: colorScheme.onSurfaceVariant,
                ),
              )
            else
              SizedBox(
                height: 300,
                child: LayoutBuilder(
                  builder: (context, constraints) {
                    final plotWidth = constraints.maxWidth - _yAxisReservedSize;
                    final stride = labelStride(
                      rows.length,
                      plotWidth,
                      _monthLabelMinWidth,
                    );
                    final rodWidth = (plotWidth / rows.length * 0.6)
                        .clamp(6.0, 32.0)
                        .toDouble();

                    return BarChart(
                      BarChartData(
                        minY: 0,
                        maxY: scale.max,
                        gridData: _horizontalGrid(colorScheme, scale.step),
                        borderData: _axisBorder(colorScheme),
                        titlesData: _monthAxisTitles(
                          months: rows.map((row) => row.month).toList(),
                          scale: scale,
                          labelStride: stride,
                          textTheme: textTheme,
                        ),
                        barTouchData: BarTouchData(
                          enabled: true,
                          touchTooltipData: BarTouchTooltipData(
                            getTooltipColor: (_) =>
                                _ChartTooltipStyle.backgroundColor,
                            fitInsideHorizontally: true,
                            fitInsideVertically: true,
                            tooltipHorizontalAlignment:
                                FLHorizontalAlignment.center,
                            getTooltipItem: (group, groupIndex, rod, rodIndex) {
                              final row = rows[group.x.toInt()];
                              return BarTooltipItem(
                                "${formatMonthYearLabel(row.month)}\n"
                                "Total: ${formatAmount(row.total)} ₽",
                                tooltipStyle.copyWith(
                                  fontWeight: FontWeight.w700,
                                ),
                                textAlign: TextAlign.start,
                                children: row.segments
                                    .map(
                                      (segment) => TextSpan(
                                        text:
                                            "\n${segment.label}: ${formatAmount(segment.amount)} ₽",
                                        style: tooltipStyle,
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
                                colorByKey[segment.key] ??
                                AppTheme.chartOtherColor;
                            stacks.add(BarChartRodStackItem(from, to, color));
                            cursor = to;
                          }

                          return BarChartGroupData(
                            x: index,
                            barRods: [
                              BarChartRodData(
                                toY: row.total,
                                rodStackItems: stacks,
                                width: rodWidth,
                                borderRadius: const BorderRadius.vertical(
                                  top: Radius.circular(4),
                                ),
                              ),
                            ],
                          );
                        }).toList(),
                      ),
                    );
                  },
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

class _ChartTooltipStyle {
  static const Color backgroundColor = Color(0xE61F2937);
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

class _TagPeriodHint extends StatelessWidget {
  const _TagPeriodHint({required this.message, required this.onShowPeriod});

  final String message;
  final VoidCallback onShowPeriod;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    return Card(
      color: colorScheme.secondaryContainer,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(
          AppTheme.space16,
          AppTheme.space8,
          AppTheme.space8,
          AppTheme.space8,
        ),
        child: Row(
          children: [
            Icon(
              Icons.date_range_rounded,
              color: colorScheme.onSecondaryContainer,
            ),
            const SizedBox(width: AppTheme.space8),
            Expanded(
              child: Text(
                message,
                style: textTheme.bodyMedium?.copyWith(
                  color: colorScheme.onSecondaryContainer,
                ),
              ),
            ),
            TextButton(
              onPressed: onShowPeriod,
              child: const Text("Show period"),
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
    super.key,
    required this.title,
    required this.color,
    required this.icon,
    required this.chartData,
    required this.emptyLabel,
  });

  final String title;
  final Color color;
  final IconData icon;
  final List<_CategoryTotal> chartData;
  final String emptyLabel;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _SectionHeader(label: title, color: color, icon: icon),
        const SizedBox(height: AppTheme.space8),
        _CategoryBreakdownCard(data: chartData, emptyLabel: emptyLabel),
      ],
    );
  }
}

/// Donut with the largest categories (the tail merged into "Other") next to a
/// ranked list of every category with its amount and share.
class _CategoryBreakdownCard extends StatefulWidget {
  const _CategoryBreakdownCard({required this.data, required this.emptyLabel});

  static const double _donutSize = 180;
  static const double _sideBySideMinWidth = 520;
  static const int _collapsedRowCount = 8;

  /// Categories sorted by total, largest first.
  final List<_CategoryTotal> data;
  final String emptyLabel;

  @override
  State<_CategoryBreakdownCard> createState() => _CategoryBreakdownCardState();
}

class _CategoryBreakdownCardState extends State<_CategoryBreakdownCard> {
  int? _touchedSliceIndex;
  bool _isExpanded = false;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final colorScheme = Theme.of(context).colorScheme;

    if (widget.data.isEmpty) {
      return Card(
        child: SizedBox(
          height: 160,
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
        ),
      );
    }

    final total = widget.data.fold<double>(0, (sum, item) => sum + item.total);
    final slices = _buildSlices(widget.data);
    final touchedIndex = _touchedSliceIndex;
    final touched = touchedIndex != null && touchedIndex < slices.length
        ? slices[touchedIndex]
        : null;

    return Card(
      child: Padding(
        padding: AppTheme.cardPadding,
        child: LayoutBuilder(
          builder: (context, constraints) {
            final donut = _buildDonut(slices, total, touched);
            final list = _buildList(total, touched);
            if (constraints.maxWidth >=
                _CategoryBreakdownCard._sideBySideMinWidth) {
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  donut,
                  const SizedBox(width: AppTheme.space24),
                  Expanded(child: list),
                ],
              );
            }
            return Column(
              children: [
                donut,
                const SizedBox(height: AppTheme.space16),
                list,
              ],
            );
          },
        ),
      ),
    );
  }

  Widget _buildDonut(
    List<_CategoryTotal> slices,
    double total,
    _CategoryTotal? touched,
  ) {
    final textTheme = Theme.of(context).textTheme;
    final colorScheme = Theme.of(context).colorScheme;
    final centerTitle = touched?.name ?? "Total";
    final centerValue = touched?.total ?? total;
    final centerShare = touched == null
        ? null
        : _formatShare(touched.total / total);

    return SizedBox(
      width: _CategoryBreakdownCard._donutSize,
      height: _CategoryBreakdownCard._donutSize,
      child: Stack(
        alignment: Alignment.center,
        children: [
          PieChart(
            PieChartData(
              centerSpaceRadius: 58,
              sectionsSpace: 2,
              sections: [
                for (var i = 0; i < slices.length; i++)
                  PieChartSectionData(
                    color: slices[i].color,
                    value: slices[i].total,
                    radius: i == _touchedSliceIndex ? 32 : 26,
                    showTitle: false,
                  ),
              ],
              pieTouchData: PieTouchData(
                enabled: true,
                touchCallback: (event, response) {
                  final index = response?.touchedSection?.touchedSectionIndex;
                  final next =
                      event.isInterestedForInteractions &&
                          index != null &&
                          index >= 0 &&
                          index < slices.length
                      ? index
                      : null;
                  if (next != _touchedSliceIndex) {
                    setState(() => _touchedSliceIndex = next);
                  }
                },
              ),
            ),
          ),
          SizedBox(
            width: 100,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  centerTitle,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  textAlign: TextAlign.center,
                  style: textTheme.labelMedium?.copyWith(
                    color: colorScheme.onSurfaceVariant,
                  ),
                ),
                FittedBox(
                  fit: BoxFit.scaleDown,
                  child: Text(
                    "${formatAmount(centerValue)} ₽",
                    style: textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                if (centerShare != null)
                  Text(
                    centerShare,
                    style: textTheme.labelMedium?.copyWith(
                      color: colorScheme.onSurfaceVariant,
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildList(double total, _CategoryTotal? touched) {
    final data = widget.data;
    final canCollapse = data.length > _CategoryBreakdownCard._collapsedRowCount;
    final visible = canCollapse && !_isExpanded
        ? data.take(_CategoryBreakdownCard._collapsedRowCount).toList()
        : data;
    final largest = data.first.total;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (final item in visible)
          _CategoryShareRow(
            color: item.color,
            label: item.name,
            amount: item.total,
            share: _formatShare(item.total / total),
            barFraction: largest > 0 ? item.total / largest : 0,
            isHighlighted:
                touched != null &&
                (touched.categoryId == item.categoryId ||
                    (touched.categoryId == _otherCategoryId &&
                        item.color == AppTheme.chartOtherColor)),
          ),
        if (canCollapse)
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton.icon(
              onPressed: () => setState(() => _isExpanded = !_isExpanded),
              icon: Icon(
                _isExpanded
                    ? Icons.expand_less_rounded
                    : Icons.expand_more_rounded,
              ),
              label: Text(
                _isExpanded ? "Show less" : "Show all ${data.length}",
              ),
            ),
          ),
      ],
    );
  }

  /// Colours the top categories from the palette and the rest grey, and
  /// returns the donut slices with the grey tail merged into one "Other".
  List<_CategoryTotal> _buildSlices(List<_CategoryTotal> totals) {
    final palette = AppTheme.chartPalette;
    final totalsById = {for (final item in totals) item.categoryId: item.total};
    // One palette slot is held back: a lone leftover key keeps its own colour.
    final topIds = topKeysByTotal(totalsById, palette.length - 1).toSet();

    final slices = <_CategoryTotal>[];
    double otherTotal = 0;
    for (final item in totals) {
      if (topIds.contains(item.categoryId)) {
        item.color = palette[slices.length];
        slices.add(item);
      } else {
        item.color = AppTheme.chartOtherColor;
        otherTotal += item.total;
      }
    }
    if (otherTotal > 0) {
      slices.add(
        _CategoryTotal(
          categoryId: _otherCategoryId,
          name: "Other",
          total: otherTotal,
          color: AppTheme.chartOtherColor,
        ),
      );
    }
    return slices;
  }

  static String _formatShare(double share) {
    final percent = share * 100;
    if (percent > 0 && percent < 1) return "<1%";
    return "${percent.round()}%";
  }
}

/// Synthetic id of the merged "Other" slice; real category ids are positive.
const int _otherCategoryId = -1;

class _CategoryShareRow extends StatelessWidget {
  const _CategoryShareRow({
    required this.color,
    required this.label,
    required this.amount,
    required this.share,
    required this.barFraction,
    required this.isHighlighted,
  });

  final Color color;
  final String label;
  final double amount;
  final String share;
  final double barFraction;
  final bool isHighlighted;

  @override
  Widget build(BuildContext context) {
    final textTheme = Theme.of(context).textTheme;
    final colorScheme = Theme.of(context).colorScheme;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppTheme.space4 + 2),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
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
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: textTheme.bodyMedium?.copyWith(
                    fontWeight: isHighlighted
                        ? FontWeight.w700
                        : FontWeight.w500,
                  ),
                ),
              ),
              const SizedBox(width: AppTheme.space8),
              Text(
                share,
                style: textTheme.labelMedium?.copyWith(
                  color: colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(width: AppTheme.space12),
              Text(
                "${formatAmount(amount)} ₽",
                style: textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppTheme.space4),
          ClipRRect(
            borderRadius: BorderRadius.circular(2),
            child: LinearProgressIndicator(
              value: barFraction,
              minHeight: 4,
              color: color,
              backgroundColor: colorScheme.surfaceContainerHighest,
            ),
          ),
        ],
      ),
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
