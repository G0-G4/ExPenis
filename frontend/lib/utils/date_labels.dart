String monthShortLabel(int month) {
  const months = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
  ];
  return months[month - 1];
}

String formatMonthYearLabel(DateTime date) {
  return "${monthShortLabel(date.month)} ${date.year}";
}

String formatDayMonthYearLabel(DateTime date) {
  return "${date.day} ${monthShortLabel(date.month)} ${date.year}";
}
