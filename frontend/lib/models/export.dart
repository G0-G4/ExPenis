import "dart:typed_data";

class ExportAccount {
  const ExportAccount({
    required this.id,
    required this.name,
    required this.currencyCode,
    required this.isDeleted,
  });
  final int id;
  final String name;
  final String currencyCode;
  final bool isDeleted;
  String get displayName => isDeleted ? "$name (удалён)" : name;
  factory ExportAccount.fromJson(Map<String, dynamic> json) => ExportAccount(
    id: json["id"] as int,
    name: json["name"] as String,
    currencyCode: json["currency_code"] as String,
    isDeleted: json["is_deleted"] as bool,
  );
}

enum ExportFormat {
  csv("csv", "text/csv"),
  xlsx(
    "xlsx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  );

  const ExportFormat(this.extension, this.mimeType);
  final String extension;
  final String mimeType;
}

class ExportRequest {
  const ExportRequest({
    this.format = ExportFormat.csv,
    this.dateFrom,
    this.dateTo,
    this.accountIds,
  });
  final ExportFormat format;
  final DateTime? dateFrom;
  final DateTime? dateTo;
  final Set<int>? accountIds;
  String? get validationError {
    if ((dateFrom == null) != (dateTo == null)) {
      return "Укажите обе границы периода";
    }
    if (dateFrom != null && dateTo != null && dateFrom!.isAfter(dateTo!)) {
      return "Начальная дата позже конечной";
    }
    if (accountIds != null && accountIds!.isEmpty) {
      return "Выберите хотя бы один счёт";
    }
    return null;
  }

  Map<String, dynamic> toQuery() {
    String date(DateTime value) =>
        "${value.year.toString().padLeft(4, "0")}-${value.month.toString().padLeft(2, "0")}-${value.day.toString().padLeft(2, "0")}";
    return {
      "format": format.extension,
      if (dateFrom != null) "date_from": date(dateFrom!),
      if (dateTo != null) "date_to": date(dateTo!),
      if (accountIds != null) "account_ids": accountIds!.toList(),
    };
  }
}

class ExportFile {
  const ExportFile({
    required this.bytes,
    required this.name,
    required this.mimeType,
  });
  final Uint8List bytes;
  final String name;
  final String mimeType;
}

enum ExportDeliveryResult { saved, handedOff, cancelled }
