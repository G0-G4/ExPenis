import 'package:expenis_mobile/models/tag_period.dart';

String normalizeTagKey(String tag) {
  return tag.trim().toLowerCase();
}

bool matchesTagFilter(
  Iterable<String> tags, {
  required Set<String> includedKeys,
  required Set<String> excludedKeys,
}) {
  final normalizedTags = {
    for (final tag in tags)
      if (normalizeTagKey(tag).isNotEmpty) normalizeTagKey(tag),
  };
  final included = {
    for (final key in includedKeys)
      if (normalizeTagKey(key).isNotEmpty) normalizeTagKey(key),
  };
  final excluded = {
    for (final key in excludedKeys)
      if (normalizeTagKey(key).isNotEmpty) normalizeTagKey(key),
  };

  if (included.isNotEmpty && !normalizedTags.any(included.contains)) {
    return false;
  }
  if (excluded.isNotEmpty && normalizedTags.any(excluded.contains)) {
    return false;
  }
  return true;
}

/// Month span covering every period whose tag is included, or null if none.
///
/// [periods] are expected to be of a single transaction type.
({DateTime firstMonth, DateTime lastMonth})? combinedTagPeriod(
  Set<String> includedKeys,
  Iterable<TagPeriod> periods,
) {
  final included = {
    for (final key in includedKeys)
      if (normalizeTagKey(key).isNotEmpty) normalizeTagKey(key),
  };
  DateTime? first;
  DateTime? last;
  for (final period in periods) {
    if (!included.contains(normalizeTagKey(period.name))) continue;
    if (first == null || period.firstAt.isBefore(first)) {
      first = period.firstAt;
    }
    if (last == null || period.lastAt.isAfter(last)) {
      last = period.lastAt;
    }
  }
  if (first == null || last == null) return null;
  return (
    firstMonth: DateTime(first.year, first.month, 1),
    lastMonth: DateTime(last.year, last.month, 1),
  );
}
