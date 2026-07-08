import 'package:flutter/material.dart';

import 'package:expenis_mobile/models/account.dart';
import 'package:expenis_mobile/screens/create_account_screen.dart';
import 'package:expenis_mobile/screens/edit_account_screen.dart';
import 'package:expenis_mobile/service/account_service.dart'
    show AccountService, AccountsResult;
import 'package:expenis_mobile/theme.dart';
import 'package:expenis_mobile/utils/format.dart';
import 'package:expenis_mobile/widgets/app_empty_state.dart';
import 'package:expenis_mobile/widgets/app_error_state.dart';

class AccountScreen extends StatefulWidget {
  const AccountScreen({super.key});

  @override
  State<AccountScreen> createState() => _AccountScreenState();
}

class _AccountScreenState extends State<AccountScreen> {
  final AccountService _accountService = AccountService();
  late Future<AccountsResult> _futureAccounts;

  @override
  void initState() {
    super.initState();
    _futureAccounts = _accountService.fetchAccounts();
  }

  void _refresh() => setState(() {
    _futureAccounts = _accountService.fetchAccounts();
  });

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

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
        title: const Text('Accounts'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            tooltip: 'Add account',
            onPressed: () async {
              final newAccount = await Navigator.push<Account>(
                context,
                MaterialPageRoute(
                  builder: (context) => const CreateAccountScreen(),
                ),
              );
              if (!mounted) return;
              if (newAccount != null) _refresh();
            },
          ),
        ],
      ),
      body: FutureBuilder<AccountsResult>(
        future: _futureAccounts,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return AppErrorState(
              message: snapshot.error.toString(),
              onRetry: _refresh,
            );
          }
          final result = snapshot.data;
          final accounts = result?.accounts ?? [];
          if (accounts.isEmpty) {
            return const AppEmptyState(
              icon: Icons.account_balance_outlined,
              title: 'No accounts yet',
              subtitle: 'Tap + to add your first account',
            );
          }

          final double total =
              result?.totalAmountRubles ??
              accounts.fold(0, (sum, a) => sum + a.amountRubles);

          return ListView(
            padding: AppTheme.screenPadding,
            children: [
              // ── Balance summary card ──────────────────────────────────
              _BalanceSummaryCard(total: total),
              const SizedBox(height: AppTheme.space16),

              // ── Account list ──────────────────────────────────────────
              Text(
                'All Accounts',
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: colorScheme.onSurfaceVariant,
                  letterSpacing: 0.5,
                ),
              ),
              const SizedBox(height: AppTheme.space8),
              ...accounts.map(
                (account) => Padding(
                  padding: const EdgeInsets.only(bottom: AppTheme.space8),
                  child: _AccountCard(
                    account: account,
                    onTap: () async {
                      final result = await Navigator.push<bool>(
                        context,
                        MaterialPageRoute(
                          builder: (context) =>
                              EditAccountScreen(accountId: account.id),
                        ),
                      );
                      if (!mounted) return;
                      if (result == true) _refresh();
                    },
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

// ── Balance Summary Card ──────────────────────────────────────────────────────

class _BalanceSummaryCard extends StatelessWidget {
  const _BalanceSummaryCard({required this.total});

  final double total;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;

    return Card(
      color: colorScheme.primaryContainer,
      shape: RoundedRectangleBorder(borderRadius: AppTheme.borderRadiusMedium),
      child: Padding(
        padding: const EdgeInsets.all(AppTheme.space24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.account_balance_wallet_outlined,
                  size: AppTheme.iconSizeMedium,
                  color: colorScheme.onPrimaryContainer.withAlpha(180),
                ),
                const SizedBox(width: AppTheme.space8),
                Text(
                  'Total Balance',
                  style: textTheme.labelLarge?.copyWith(
                    color: colorScheme.onPrimaryContainer.withAlpha(180),
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppTheme.space8),
            Text(
              '${formatAmount(total)} ₽',
              style: textTheme.headlineMedium?.copyWith(
                color: colorScheme.onPrimaryContainer,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Account Card ─────────────────────────────────────────────────────────────

class _AccountCard extends StatelessWidget {
  const _AccountCard({required this.account, required this.onTap});

  final Account account;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;

    final isPositive = account.amountRubles >= 0;
    final amountColor = isPositive
        ? AppTheme.incomeColor
        : AppTheme.expenseColor;
    final showSecondary = account.currencyCode != 'RUB';

    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: AppTheme.borderRadiusMedium,
        child: Padding(
          padding: AppTheme.cardPadding,
          child: Row(
            children: [
              // Icon container
              Container(
                width: AppTheme.iconBoxSize,
                height: AppTheme.iconBoxSize,
                decoration: BoxDecoration(
                  color: colorScheme.secondaryContainer,
                  borderRadius: AppTheme.borderRadiusSmall,
                ),
                child: Icon(
                  Icons.account_balance_outlined,
                  size: AppTheme.iconSizeLarge,
                  color: colorScheme.onSecondaryContainer,
                ),
              ),
              const SizedBox(width: AppTheme.space12),
              // Name + currency
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      account.name,
                      style: textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: AppTheme.space2),
                    Text(
                      account.currencyCode,
                      style: textTheme.bodySmall?.copyWith(
                        color: colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
              // Amount (primary: rubles; secondary: native currency if not RUB)
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    '${formatAmount(account.amountRubles)} ₽',
                    style: textTheme.titleMedium?.copyWith(
                      color: amountColor,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  if (showSecondary)
                    Text(
                      '${formatAmount(account.amount)} ${account.currencyCode}',
                      style: textTheme.bodySmall?.copyWith(
                        color: colorScheme.onSurfaceVariant,
                      ),
                    ),
                ],
              ),
              const SizedBox(width: AppTheme.space4),
              Icon(
                Icons.chevron_right_rounded,
                color: colorScheme.outlineVariant,
                size: AppTheme.iconSizeMedium,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
