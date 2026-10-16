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
    required this.onSelectAllCategories,
    required this.onClearAllCategories,
    required this.tagLabelsByKey,
    this.outOfPeriodTagLabelsByKey = const {},
    required this.includedTagKeys,
    required this.excludedTagKeys,
    required this.onCycleTag,
    required this.onSetTagSelection,
    this.title = "Filters",
  });

  static const double _maxChipAreaHeight = 156;

  final String title;
  final Color accentColor;
  final List<Category> categories;
  final Set<int> selectedCategoryIds;
  final ValueChanged<int> onToggleCategory;
  final VoidCallback onSelectAllCategories;
  final VoidCallback onClearAllCategories;

  /// Tags present in the loaded period.
  final Map<String, String> tagLabelsByKey;

  /// Tags used before but absent from the loaded period; shown dimmed.
  final Map<String, String> outOfPeriodTagLabelsByKey;
  final Set<String> includedTagKeys;
  final Set<String> excludedTagKeys;
  final ValueChanged<String> onCycleTag;
  final void Function(Set<String> includedKeys, Set<String> excludedKeys)
  onSetTagSelection;

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    final sortedTagKeys = _sortedKeys(tagLabelsByKey);
    final sortedOutOfPeriodTagKeys = _sortedKeys(outOfPeriodTagLabelsByKey);
    final totalTagCount =
        sortedTagKeys.length + sortedOutOfPeriodTagKeys.length;
    final selectedCategoryCount = categories
        .where((category) => selectedCategoryIds.contains(category.id))
        .length;
    final includedTagCount = includedTagKeys.length;
    final excludedTagCount = excludedTagKeys.length;
    final categorySummary =
        "$selectedCategoryCount/${categories.length} selected";
    final tagSummary = includedTagCount == 0 && excludedTagCount == 0
        ? "0/$totalTagCount selected"
        : "$includedTagCount included · $excludedTagCount excluded";

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
                onSelectAll: categories.isEmpty ? null : onSelectAllCategories,
                onClearAll: selectedCategoryCount == 0
                    ? null
                    : onClearAllCategories,
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
                    : () =>
                          onSetTagSelection(sortedTagKeys.toSet(), <String>{}),
                onClearAll: includedTagCount == 0 && excludedTagCount == 0
                    ? null
                    : () => onSetTagSelection(<String>{}, <String>{}),
              ),
              const SizedBox(height: AppTheme.space8),
              if (totalTagCount == 0)
                Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    "No tags",
                    style: textTheme.bodySmall?.copyWith(
                      color: colorScheme.onSurfaceVariant,
                    ),
                  ),
                )
              else
                _buildScrollableChipArea(
                  child: _TagChips(
                    accentColor: accentColor,
                    inPeriodKeys: sortedTagKeys,
                    outOfPeriodKeys: sortedOutOfPeriodTagKeys,
                    labelFor: (tagKey) =>
                        tagLabelsByKey[tagKey] ??
                        outOfPeriodTagLabelsByKey[tagKey] ??
                        tagKey,
                    includedTagKeys: includedTagKeys,
                    excludedTagKeys: excludedTagKeys,
                    onCycleTag: onCycleTag,
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }

  static List<String> _sortedKeys(Map<String, String> labelsByKey) {
    return labelsByKey.keys.toList()..sort(
      (a, b) => labelsByKey[a]!.toLowerCase().compareTo(
        labelsByKey[b]!.toLowerCase(),
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

class _TagChips extends StatefulWidget {
  const _TagChips({
    required this.accentColor,
    required this.inPeriodKeys,
    required this.outOfPeriodKeys,
    required this.labelFor,
    required this.includedTagKeys,
    required this.excludedTagKeys,
    required this.onCycleTag,
  });

  final Color accentColor;
  final List<String> inPeriodKeys;
  final List<String> outOfPeriodKeys;
  final String Function(String tagKey) labelFor;
  final Set<String> includedTagKeys;
  final Set<String> excludedTagKeys;
  final ValueChanged<String> onCycleTag;

  @override
  State<_TagChips> createState() => _TagChipsState();
}

class _TagChipsState extends State<_TagChips> {
  bool _showOutOfPeriod = false;

  bool _isActive(String tagKey) =>
      widget.includedTagKeys.contains(tagKey) ||
      widget.excludedTagKeys.contains(tagKey);

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    // Selected out-of-period tags stay visible while the rest is collapsed.
    final pinnedKeys = widget.outOfPeriodKeys.where(_isActive).toList();
    final hiddenKeys = widget.outOfPeriodKeys
        .where((tagKey) => !_isActive(tagKey))
        .toList();
    final shownOutOfPeriodKeys = _showOutOfPeriod
        ? widget.outOfPeriodKeys
        : pinnedKeys;

    return Wrap(
      spacing: AppTheme.space8,
      runSpacing: AppTheme.space8,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        for (final tagKey in widget.inPeriodKeys)
          _buildChip(context, tagKey, dimmed: false),
        for (final tagKey in shownOutOfPeriodKeys)
          _buildChip(context, tagKey, dimmed: true),
        if (hiddenKeys.isNotEmpty)
          TextButton(
            onPressed: () =>
                setState(() => _showOutOfPeriod = !_showOutOfPeriod),
            child: Text(
              _showOutOfPeriod
                  ? "Hide other periods"
                  : "${hiddenKeys.length} more from other periods",
              style: textTheme.labelMedium?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
            ),
          ),
      ],
    );
  }

  Widget _buildChip(
    BuildContext context,
    String tagKey, {
    required bool dimmed,
  }) {
    final colorScheme = Theme.of(context).colorScheme;
    final textTheme = Theme.of(context).textTheme;
    final accentColor = widget.accentColor;
    final isIncluded = widget.includedTagKeys.contains(tagKey);
    final isExcluded = widget.excludedTagKeys.contains(tagKey);
    final chip = FilterChip(
      label: Text(widget.labelFor(tagKey)),
      selected: isIncluded,
      onSelected: (_) => widget.onCycleTag(tagKey),
      showCheckmark: false,
      selectedColor: accentColor.withAlpha(30),
      backgroundColor: dimmed
          ? colorScheme.surface
          : colorScheme.surfaceContainerLow,
      checkmarkColor: accentColor,
      side: BorderSide(
        color: isExcluded ? colorScheme.outline : colorScheme.outlineVariant,
      ),
      labelStyle: textTheme.labelMedium?.copyWith(
        color: isIncluded
            ? accentColor
            : isExcluded
            ? colorScheme.onSurfaceVariant
            : colorScheme.onSurface,
        fontWeight: FontWeight.w600,
        decoration: isExcluded
            ? TextDecoration.lineThrough
            : TextDecoration.none,
        decorationColor: isExcluded ? colorScheme.onSurfaceVariant : null,
      ),
    );
    if (!dimmed) return chip;
    return Opacity(opacity: 0.6, child: chip);
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
