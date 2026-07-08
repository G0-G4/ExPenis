import "package:flutter/material.dart";

import "package:expenis_mobile/theme.dart";
import "package:expenis_mobile/utils/date_labels.dart";

Future<DateTime?> showMonthPickerBottomSheet({
  required BuildContext context,
  required DateTime initialMonth,
  String? titlePrefix,
}) async {
  final now = DateTime.now();

  return showModalBottomSheet<DateTime>(
    context: context,
    showDragHandle: true,
    useSafeArea: true,
    builder: (context) {
      var selectedYear = initialMonth.year;
      final textTheme = Theme.of(context).textTheme;
      final colorScheme = Theme.of(context).colorScheme;

      return StatefulBuilder(
        builder: (context, setSheetState) {
          final canGoPrevYear = selectedYear > 2000;
          final canGoNextYear = selectedYear < now.year;

          return Padding(
            padding: const EdgeInsets.fromLTRB(
              AppTheme.space16,
              0,
              AppTheme.space16,
              AppTheme.space16,
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Row(
                  children: [
                    IconButton(
                      onPressed: canGoPrevYear
                          ? () => setSheetState(() => selectedYear -= 1)
                          : null,
                      icon: const Icon(Icons.chevron_left_rounded),
                    ),
                    Expanded(
                      child: Center(
                        child: Text(
                          titlePrefix == null
                              ? selectedYear.toString()
                              : "$titlePrefix: $selectedYear",
                          style: textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                    ),
                    IconButton(
                      onPressed: canGoNextYear
                          ? () => setSheetState(() => selectedYear += 1)
                          : null,
                      icon: const Icon(Icons.chevron_right_rounded),
                    ),
                  ],
                ),
                const SizedBox(height: AppTheme.space8),
                GridView.builder(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: 12,
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 3,
                    mainAxisSpacing: AppTheme.space8,
                    crossAxisSpacing: AppTheme.space8,
                    childAspectRatio: 2.2,
                  ),
                  itemBuilder: (context, index) {
                    final month = index + 1;
                    final monthDate = DateTime(selectedYear, month, 1);
                    final isFutureMonth =
                        selectedYear == now.year && month > now.month;
                    final isSelected =
                        selectedYear == initialMonth.year &&
                        month == initialMonth.month;
                    return FilledButton.tonal(
                      onPressed: isFutureMonth
                          ? null
                          : () => Navigator.pop(context, monthDate),
                      style: FilledButton.styleFrom(
                        backgroundColor: isSelected
                            ? colorScheme.primaryContainer
                            : colorScheme.surfaceContainerLow,
                        foregroundColor: isSelected
                            ? colorScheme.onPrimaryContainer
                            : colorScheme.onSurface,
                      ),
                      child: Text(monthShortLabel(month)),
                    );
                  },
                ),
              ],
            ),
          );
        },
      );
    },
  );
}
