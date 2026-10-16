Set<T> toggledSetValue<T>(Set<T> source, T value) {
  final next = <T>{...source};
  if (next.contains(value)) {
    next.remove(value);
  } else {
    next.add(value);
  }
  return next;
}

({Set<T> included, Set<T> excluded}) cycleTagFilter<T>(
  Set<T> included,
  Set<T> excluded,
  T key,
) {
  final nextIncluded = <T>{...included};
  final nextExcluded = <T>{...excluded};
  if (nextIncluded.contains(key)) {
    nextIncluded.remove(key);
    nextExcluded.add(key);
  } else if (nextExcluded.contains(key)) {
    nextExcluded.remove(key);
  } else {
    nextIncluded.add(key);
  }
  return (included: nextIncluded, excluded: nextExcluded);
}

/// Selection shown for a period. A `null` [explicit] set means "all": every
/// available value is selected, including ones that appear later.
Set<T> effectiveSelection<T>(Set<T>? explicit, Set<T> available) {
  if (explicit == null) return <T>{...available};
  return explicit.intersection(available);
}

/// Toggles [value]; toggling from "all" fixes the currently available set.
Set<T> toggledExplicitSelection<T>(
  Set<T>? explicit,
  Set<T> available,
  T value,
) {
  return toggledSetValue(explicit ?? available, value);
}

Set<T> intersectOrKeepEmpty<T>(Set<T> selected, Set<T> available) {
  if (selected.isEmpty) return <T>{};
  final next = selected.intersection(available);
  return next.isEmpty && available.isNotEmpty ? <T>{...available} : next;
}
