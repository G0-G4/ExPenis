import 'dart:io';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:expenis_mobile/service/settings_service.dart';

abstract class BaseService {
  late final Dio _dio;

  BaseService() {
    _dio = Dio(
      BaseOptions(
        validateStatus: (status) {
          return status! >= 200 && status < 500;
        },
      ),
    );

    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final settingsService = await SettingsService.getInstance();
          final apiKey = await settingsService.getApiKey();

          if (apiKey != null && apiKey.isNotEmpty) {
            options.headers['Authorization'] = apiKey;
          }

          handler.next(options);
        },
      ),
    );
  }

  Dio get dio => _dio;

  String get baseUrl {
    if (kReleaseMode) {
      return 'https://expenis.g0g4.ru';
    }

    return kIsWeb
        ? 'http://localhost:8000'
        : Platform.isAndroid
        ? 'http://10.0.2.2:8000'
        : 'http://192.168.1.5:8000';
  }
}
