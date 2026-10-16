import "dart:math" as math;

/// Y-axis bounds and tick step rounded to human-friendly values.
class AxisScale {
  const AxisScale({required this.min, required this.max, required this.step});

  final double min;
  final double max;
  final double step;
}

/// Expands [minValue]..[maxValue] outwards so that both bounds and the tick
/// step are "nice" numbers (1, 2, 2.5 or 5 × 10ⁿ), giving roughly
/// [targetTicks] intervals.
AxisScale niceAxisScale(
  double minValue,
  double maxValue, {
  int targetTicks = 4,
}) {
  var lo = minValue;
  var hi = maxValue;
  if (hi <= lo) hi = lo + targetTicks;

  final rawStep = (hi - lo) / targetTicks;
  final magnitude = math
      .pow(10, (math.log(rawStep) / math.ln10).floor())
      .toDouble();
  final residual = rawStep / magnitude;
  final niceResidual = residual <= 1
      ? 1.0
      : residual <= 2
      ? 2.0
      : residual <= 2.5
      ? 2.5
      : residual <= 5
      ? 5.0
      : 10.0;
  final step = niceResidual * magnitude;

  lo = (lo / step).floor() * step;
  hi = (hi / step).ceil() * step;
  return AxisScale(min: lo, max: hi, step: step);
}

/// Short axis label: 1 500 → "1.5k", 2 000 000 → "2M".
String compactAmount(double value) {
  final absolute = value.abs();
  if (absolute >= 1000000) return "${_trimDecimal(value / 1000000)}M";
  if (absolute >= 1000) return "${_trimDecimal(value / 1000)}k";
  return _trimDecimal(value);
}

String _trimDecimal(double value) {
  final fixed = value.toStringAsFixed(1);
  return fixed.endsWith(".0") ? fixed.substring(0, fixed.length - 2) : fixed;
}

/// How many axis labels to skip so that [count] labels of [minLabelWidth]
/// fit into [availableWidth]. Returns 1 when every label fits.
int labelStride(int count, double availableWidth, double minLabelWidth) {
  if (count <= 0 || availableWidth <= 0) return 1;
  return math.max(1, (count * minLabelWidth / availableWidth).ceil());
}

/// Keys of [totals] ranked by value, limited to the [limit] largest.
///
/// The remainder is meant to be merged into a single "Other" bucket, so when
/// only one key would be left over it is kept instead (an "Other" bucket with
/// a single item is just a worse label).
List<K> topKeysByTotal<K>(Map<K, double> totals, int limit) {
  final ranked = totals.keys.toList()
    ..sort((a, b) => totals[b]!.compareTo(totals[a]!));
  if (ranked.length <= limit + 1) return ranked;
  return ranked.sublist(0, limit);
}
