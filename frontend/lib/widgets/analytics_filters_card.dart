import "package:flutter/material.dart";

import "package:expenis_mobile/models/category.dart";
import "package:expenis_mobile/theme.dart";

class AnalyticsFiltersCard extends StatelessWidget {
  const AnalyticsFiltersCard({
    super.key,
    required this.accentColor,
    required this.categories,
    required this.selectedCategoryIds,
    required this.onToggleCategory,
    required this.onSetCategorySelection,
    required this.tagLabelsByKey,
    required this.selectedTagKeys,
    required this.onToggleTag,
    required this.onSetTagSelection,
    this.title = "Filters",
  });

  static const double _maxChipAreaHeight = 156;

  final String title;
  final Color accentColor;
  final List<Category> categories;
  final Set<int> selectedCategoryIds;
  final ValueChanged<int> onToggleCategory;
  final ValueChanged<Set<int>> onSetCategorySelection;
  final Map<String, String> tagLabelsByKey;
  final Set<String> selectedTagKeys;
  final ValueChanged<String> onToggleTag;
  final ValueChanged<Set<String>> onSetTagSelection;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    final sortedTagKeys = tagLabelsByKey.keys.toList()
      ..sort(
        (a, b) => tagLabelsByKey[a]!.toLowerCase().compareTo(
          tagLabelsByKey[b]!.toLowerCase(),
        ),
      );
    final selectedCategoryCount = categories
        .where((category) => selectedCategoryIds.contains(category.id))
        .length;
    final selectedTagCount = sortedTagKeys
        .where((tagKey) => selectedTagKeys.contains(tagKey))
        .length;
    final categorySummary =
        "$selectedCategoryCount/${categories.length} selected";
    final tagSummary = "$selectedTagCount/${sortedTagKeys.length} selected";

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
                  title,
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
                onClearAll: selectedCategoryCount == 0
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
                onSelectAll: sortedTagKeys.isEmpty
                    ? null
                    : () => onSetTagSelection(sortedTagKeys.toSet()),
                onClearAll: selectedTagCount == 0
                    ? null
                    : () => onSetTagSelection(<String>{}),
              ),
              const SizedBox(height: AppTheme.space8),
              if (sortedTagKeys.isEmpty)
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
                    children: sortedTagKeys
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
    return AnimatedSize(
      duration: const Duration(milliseconds: 180),
      curve: Curves.easeOut,
      alignment: Alignment.topCenter,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxHeight: _maxChipAreaHeight),
        child: Scrollbar(
          child: SingleChildScrollView(
            child: Align(alignment: Alignment.topLeft, child: child),
          ),
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
