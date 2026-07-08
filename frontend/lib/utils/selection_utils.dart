Set<T> toggledSetValue<T>(Set<T> source, T value) {
  final next = <T>{...source};
  if (next.contains(value)) {
    next.remove(value);
  } else {
    next.add(value);
  }
  return next;
}

Set<T> intersectOrAll<T>(Set<T> selected, Set<T> available) {
  final next = selected.intersection(available);
  return next.isEmpty ? <T>{...available} : next;
}

Set<T> intersectOrKeepEmpty<T>(Set<T> selected, Set<T> available) {
  if (selected.isEmpty) return <T>{};
  final next = selected.intersection(available);
  return next.isEmpty && available.isNotEmpty ? <T>{...available} : next;
}
