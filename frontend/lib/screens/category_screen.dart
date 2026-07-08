import 'package:flutter/material.dart';

import 'package:expenis_mobile/models/category.dart';
import 'package:expenis_mobile/screens/create_category_screen.dart';
import 'package:expenis_mobile/screens/edit_category_screen.dart';
import 'package:expenis_mobile/service/category_service.dart';
import 'package:expenis_mobile/theme.dart';
import 'package:expenis_mobile/widgets/app_empty_state.dart';
import 'package:expenis_mobile/widgets/app_error_state.dart';

class CategoryScreen extends StatefulWidget {
  const CategoryScreen({super.key});

  @override
  State<CategoryScreen> createState() => _CategoryScreenState();
}

class _CategoryScreenState extends State<CategoryScreen> {
  final CategoryService _categoryService = CategoryService();
  late Future<List<Category>> _futureCategories;

  @override
  void initState() {
    super.initState();
    _futureCategories = _categoryService.fetchCategories();
  }

  void _refresh() => setState(() {
    _futureCategories = _categoryService.fetchCategories();
  });

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
        title: const Text('Categories'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            tooltip: 'Add category',
            onPressed: () async {
              final newCategory = await Navigator.push<Category>(
                context,
                MaterialPageRoute(
                  builder: (context) => const CreateCategoryScreen(),
                ),
              );
              if (!mounted) return;
              if (newCategory != null) _refresh();
            },
          ),
        ],
      ),
      body: FutureBuilder<List<Category>>(
        future: _futureCategories,
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
          final categories = snapshot.data ?? [];
          if (categories.isEmpty) {
            return const AppEmptyState(
              icon: Icons.folder_outlined,
              title: 'No categories yet',
              subtitle: 'Tap + to add your first category',
            );
          }

          final income = categories
              .where((c) => c.type == CategoryType.income)
              .toList();
          final expense = categories
              .where((c) => c.type == CategoryType.expense)
              .toList();

          return ListView(
            padding: AppTheme.screenPadding,
            children: [
              if (income.isNotEmpty) ...[
                _CategorySectionHeader(
                  label: 'Income',
                  color: AppTheme.incomeColor,
                  icon: Icons.arrow_downward_rounded,
                ),
                const SizedBox(height: AppTheme.space8),
                ..._buildCategoryCards(income),
                const SizedBox(height: AppTheme.space16),
              ],
              if (expense.isNotEmpty) ...[
                _CategorySectionHeader(
                  label: 'Expenses',
                  color: AppTheme.expenseColor,
                  icon: Icons.arrow_upward_rounded,
                ),
                const SizedBox(height: AppTheme.space8),
                ..._buildCategoryCards(expense),
              ],
            ],
          );
        },
      ),
    );
  }

  List<Widget> _buildCategoryCards(List<Category> categories) {
    return categories.map((category) {
      return Padding(
        padding: const EdgeInsets.only(bottom: AppTheme.space8),
        child: _CategoryCard(
          category: category,
          onTap: () async {
            final result = await Navigator.push<bool>(
              context,
              MaterialPageRoute(
                builder: (context) =>
                    EditCategoryScreen(categoryId: category.id),
              ),
            );
            if (!mounted) return;
            if (result == true) _refresh();
          },
        ),
      );
    }).toList();
  }
}

// ── Section Header ────────────────────────────────────────────────────────────

class _CategorySectionHeader extends StatelessWidget {
  const _CategorySectionHeader({
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

// ── Category Card ─────────────────────────────────────────────────────────────

class _CategoryCard extends StatelessWidget {
  const _CategoryCard({required this.category, required this.onTap});

  final Category category;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    final isIncome = category.type == CategoryType.income;
    final typeColor = isIncome ? AppTheme.incomeColor : AppTheme.expenseColor;
    final typeBgColor = isIncome
        ? AppTheme.incomeColorLight
        : AppTheme.expenseColorLight;

    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: AppTheme.borderRadiusMedium,
        child: Padding(
          padding: AppTheme.cardPadding,
          child: Row(
            children: [
              // Type icon
              Container(
                width: AppTheme.iconBoxSize,
                height: AppTheme.iconBoxSize,
                decoration: BoxDecoration(
                  color: typeBgColor,
                  borderRadius: AppTheme.borderRadiusSmall,
                ),
                child: Icon(
                  isIncome
                      ? Icons.arrow_downward_rounded
                      : Icons.arrow_upward_rounded,
                  size: AppTheme.iconSizeMedium,
                  color: typeColor,
                ),
              ),
              const SizedBox(width: AppTheme.space12),
              // Name
              Expanded(
                child: Text(
                  category.name,
                  style: textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              // Type badge
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppTheme.space8,
                  vertical: AppTheme.space4,
                ),
                decoration: BoxDecoration(
                  color: typeBgColor,
                  borderRadius: AppTheme.borderRadiusSmall,
                ),
                child: Text(
                  isIncome ? 'Income' : 'Expense',
                  style: textTheme.labelSmall?.copyWith(
                    color: typeColor,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              const SizedBox(width: AppTheme.space8),
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
