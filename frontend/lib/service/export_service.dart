import "dart:convert";
import "dart:typed_data";

import "package:dio/dio.dart";

import "package:expenis_mobile/models/export.dart";
import "package:expenis_mobile/service/base_service.dart";

class ExportService extends BaseService {
  Future<List<ExportAccount>> fetchAccounts() async {
    try {
      final response = await dio.get("$baseUrl/api/exports/accounts");
      if (response.statusCode != 200) {
        throw Exception("Не удалось загрузить счета");
      }
      return ((response.data as Map<String, dynamic>)["accounts"] as List)
          .map((value) => ExportAccount.fromJson(value as Map<String, dynamic>))
          .toList();
    } on DioException catch (_) {
      throw Exception(
        "Не удалось загрузить счета. Проверьте соединение и повторите",
      );
    }
  }

  Future<ExportFile> export(ExportRequest request) async {
    if (request.validationError != null) {
      throw Exception(request.validationError);
    }
    try {
      final response = await dio.get<List<int>>(
        "$baseUrl/api/exports/transactions",
        queryParameters: request.toQuery(),
        options: Options(
          responseType: ResponseType.bytes,
          listFormat: ListFormat.multi,
        ),
      );
      final mime = response.headers
          .value(Headers.contentTypeHeader)
          ?.split(";")
          .first
          .trim();
      if (response.statusCode != 200 || mime != request.format.mimeType) {
        String message =
            "Не удалось экспортировать операции. Повторите попытку";
        try {
          final body = jsonDecode(utf8.decode(response.data ?? []));
          if (body is Map && body["detail"] is String) {
            message = body["detail"] as String;
          }
        } on FormatException {
          /* Keep the readable fallback for non-JSON responses. */
        }
        throw Exception(message);
      }
      final disposition = response.headers.value("content-disposition") ?? "";
      final candidate = RegExp(
        "filename=\"?([^\";]+)",
      ).firstMatch(disposition)?.group(1);
      final name =
          candidate != null &&
              RegExp(r"^[a-zA-Z0-9_.-]+$").hasMatch(candidate) &&
              candidate.endsWith(".${request.format.extension}")
          ? candidate
          : "ExPenis-transactions.${request.format.extension}";
      return ExportFile(
        bytes: Uint8List.fromList(response.data ?? []),
        name: name,
        mimeType: request.format.mimeType,
      );
    } on DioException catch (_) {
      throw Exception(
        "Не удалось экспортировать операции. Проверьте соединение и повторите",
      );
    }
  }
}
