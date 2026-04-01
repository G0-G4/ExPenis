import 'package:flutter/material.dart';

import 'package:expenis_mobile/models/transaction.dart';
import 'package:expenis_mobile/screens/edit_transaction_screen.dart';
import 'package:expenis_mobile/screens/transaction_stats_screen.dart';
import 'package:expenis_mobile/service/transaction_service.dart';
import 'package:expenis_mobile/theme.dart';
import 'package:expenis_mobile/utils/format.dart';
import 'package:expenis_mobile/widgets/app_empty_state.dart';
import 'package:expenis_mobile/widgets/app_error_state.dart';

class TransactionScreen extends StatefulWidget {
  const TransactionScreen({super.key});

  @override
  State<TransactionScreen> createState() => _TransactionScreenState();
}

class _TransactionScreenState extends State<TransactionScreen> {
  final TransactionService _transactionService = TransactionService();
  DateTime _selectedDate = DateTime.now();

  List<Transaction> _transactions = [];
  bool _isFirstLoad = true;
  bool _isLoading = false;
  String? _loadError;

  @override
  void initState() {
    super.initState();
    _loadTransactions();
  }

  Future<void> _loadTransactions() async {
    final targetDate = _selectedDate;
    setState(() {
      _isLoading = true;
      _loadError = null;
    });
    try {
      final data = await _transactionService.fetchTransactions(
        dateFrom: targetDate,
        dateTo: targetDate,
      );
      if (!mounted) return;
      setState(() {
        _transactions = data;
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

  void _changeDate(int days) {
    setState(() {
      _selectedDate = _selectedDate.add(Duration(days: days));
    });
    _loadTransactions();
  }

  Future<void> _selectDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _selectedDate,
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
    );
    if (picked == null || !mounted) return;
    setState(() {
      _selectedDate = picked;
    });
    _loadTransactions();
  }

  void _refresh() => _loadTransactions();

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
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final d = DateTime(date.year, date.month, date.day);
    if (d == today) return 'Today';
    if (d == today.subtract(const Duration(days: 1))) return 'Yesterday';
    if (d == today.add(const Duration(days: 1))) return 'Tomorrow';
    return '${date.day} ${months[date.month - 1]} ${date.year}';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: Builder(
          builder: (context) => IconButton(
            icon: const Icon(Icons.menu),
            tooltip: 'Open menu',
            onPressed: () => context
                .findRootAncestorStateOfType<ScaffoldState>()
                ?.openDrawer(),
          ),
        ),
        title: const Text('Transactions'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            tooltip: 'Add transaction',
            onPressed: () async {
              final result = await Navigator.push<bool>(
                context,
                MaterialPageRoute(
                  builder: (context) =>
                      EditTransactionScreen(initialDate: _selectedDate),
                ),
              );
              if (!mounted) return;
              if (result == true) _refresh();
            },
          ),
        ],
      ),
      body: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onHorizontalDragEnd: (details) {
          final v = details.primaryVelocity ?? 0;
          if (v < -200) _changeDate(1);
          if (v > 200) _changeDate(-1);
        },
        child: Column(
          children: [
            // ── Date navigation bar ───────────────────────────────────
            _DateNavBar(
              label: _formatDate(_selectedDate),
              onPrevious: () => _changeDate(-1),
              onNext: () => _changeDate(1),
              onTap: _selectDate,
            ),

            // ── Loading indicator (outside AnimatedSwitcher) ──────────
            AnimatedContainer(
              duration: const Duration(milliseconds: 150),
              height: _isLoading ? 2.0 : 0.0,
              child: _isLoading
                  ? const LinearProgressIndicator()
                  : const SizedBox.shrink(),
            ),

            // ── Transaction list ──────────────────────────────────────
            Expanded(
              child: _isFirstLoad && _isLoading
                  ? const Center(child: CircularProgressIndicator())
                  : _buildContent(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildContent() {
    if (_loadError != null) {
      return AppErrorState(message: _loadError!, onRetry: _refresh);
    }

    if (_transactions.isEmpty) {
      return const AppEmptyState(
        icon: Icons.swap_horiz_outlined,
        title: 'No transactions',
        subtitle: 'Tap + to record a transaction',
      );
    }

    final income = _transactions
        .where((t) => t.type == TransactionType.income)
        .toList();
    final expense = _transactions
        .where((t) => t.type == TransactionType.expense)
        .toList();
    final incomeTotal = income.fold<double>(0, (s, t) => s + t.amountRubles);
    final expenseTotal = expense.fold<double>(0, (s, t) => s + t.amountRubles);

    return ListView(
      padding: AppTheme.screenPadding,
      children: [
        _DailySummaryCard(
          incomeTotal: incomeTotal,
          expenseTotal: expenseTotal,
          onTap: _openStats,
        ),
        const SizedBox(height: AppTheme.space16),
        if (income.isNotEmpty) ...[
          _SectionHeader(
            label: 'Income',
            color: AppTheme.incomeColor,
            icon: Icons.arrow_downward_rounded,
          ),
          const SizedBox(height: AppTheme.space8),
          ...income.map(
            (t) => Padding(
              padding: const EdgeInsets.only(bottom: AppTheme.space8),
              child: _TransactionCard(
                transaction: t,
                onTap: () => _openEdit(t),
              ),
            ),
          ),
          const SizedBox(height: AppTheme.space8),
        ],
        if (expense.isNotEmpty) ...[
          _SectionHeader(
            label: 'Expenses',
            color: AppTheme.expenseColor,
            icon: Icons.arrow_upward_rounded,
          ),
          const SizedBox(height: AppTheme.space8),
          ...expense.map(
            (t) => Padding(
              padding: const EdgeInsets.only(bottom: AppTheme.space8),
              child: _TransactionCard(
                transaction: t,
                onTap: () => _openEdit(t),
              ),
            ),
          ),
        ],
      ],
    );
  }

  Future<void> _openEdit(Transaction t) async {
    final result = await Navigator.push<bool>(
      context,
      MaterialPageRoute(
        builder: (context) => EditTransactionScreen(transactionId: t.id),
      ),
    );
    if (!mounted) return;
    if (result == true) _refresh();
  }

  Future<void> _openStats() async {
    await Navigator.push<void>(
      context,
      MaterialPageRoute(
        builder: (context) =>
            TransactionStatsScreen(initialEndDate: _selectedDate),
      ),
    );
  }
}

// ── Date Navigation Bar ───────────────────────────────────────────────────────

class _DateNavBar extends StatelessWidget {
  const _DateNavBar({
    required this.label,
    required this.onPrevious,
    required this.onNext,
    required this.onTap,
  });

  final String label;
  final VoidCallback onPrevious;
  final VoidCallback onNext;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    return Container(
      color: colorScheme.surface,
      padding: const EdgeInsets.symmetric(
        horizontal: AppTheme.space8,
        vertical: AppTheme.space4,
      ),
      child: Row(
        children: [
          IconButton(
            icon: const Icon(Icons.chevron_left_rounded),
            onPressed: onPrevious,
            style: IconButton.styleFrom(
              foregroundColor: colorScheme.onSurfaceVariant,
            ),
          ),
          Expanded(
            child: GestureDetector(
              onTap: onTap,
              behavior: HitTestBehavior.opaque,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    label,
                    textAlign: TextAlign.center,
                    style: textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(width: AppTheme.space4),
                  Icon(
                    Icons.expand_more_rounded,
                    size: AppTheme.iconSizeMedium,
                    color: colorScheme.onSurfaceVariant,
                  ),
                ],
              ),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.chevron_right_rounded),
            onPressed: onNext,
            style: IconButton.styleFrom(
              foregroundColor: colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );
  }
}

// ── Daily Summary Card ────────────────────────────────────────────────────────

class _DailySummaryCard extends StatelessWidget {
  const _DailySummaryCard({
    required this.incomeTotal,
    required this.expenseTotal,
    required this.onTap,
  });

  final double incomeTotal;
  final double expenseTotal;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    final net = incomeTotal - expenseTotal;
    final isPositive = net >= 0;

    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: AppTheme.borderRadiusMedium,
        child: Padding(
          padding: AppTheme.cardPadding,
          child: Column(
            children: [
              Row(
                children: [
                  _SummaryItem(
                    label: 'Income',
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
                    label: 'Expenses',
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
                    'Net',
                    style: textTheme.bodyMedium?.copyWith(
                      color: colorScheme.onSurfaceVariant,
                    ),
                  ),
                  Text(
                    '${isPositive ? '+' : ''}${formatAmount(net.abs())} ₽',
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
                    '$fmt ₽',
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

// ── Section Header ────────────────────────────────────────────────────────────

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
          label,
          style: Theme.of(context).textTheme.labelMedium?.copyWith(
            color: color,
            fontWeight: FontWeight.w700,
            letterSpacing: 0.4,
          ),
        ),
      ],
    );
  }
}

// ── Transaction Card ──────────────────────────────────────────────────────────

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
    final showSecondary = transaction.currencyCode != 'RUB';
    final nativeAmountStr = formatAmount(transaction.amount);

    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: AppTheme.borderRadiusMedium,
        child: Padding(
          padding: AppTheme.cardPadding,
          child: Row(
            children: [
              // Category icon container
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
              // Details
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
                            ' · ',
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
              // Amount (primary: rubles; secondary: native currency if not RUB)
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    '${isIncome ? '+' : '-'}$amountRublesStr ₽',
                    style: textTheme.titleSmall?.copyWith(
                      color: amountColor,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  if (showSecondary)
                    Text(
                      '${isIncome ? '+' : '-'}$nativeAmountStr ${transaction.currencyCode}',
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
