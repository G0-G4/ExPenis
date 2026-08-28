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
