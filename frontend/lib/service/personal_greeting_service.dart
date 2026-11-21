import "package:dio/dio.dart";

import "package:expenis_mobile/models/personal_greeting.dart";
import "package:expenis_mobile/service/base_service.dart";

class PersonalGreetingService extends BaseService {
  Future<PersonalGreeting?> fetchGreeting() async {
    try {
      final response = await dio.get("$baseUrl/api/me/greeting");
      if (response.statusCode != 200) {
        throw Exception("Failed to load greeting (${response.statusCode})");
      }
      final json = response.data["greeting"];
      return json == null
          ? null
          : PersonalGreeting.fromJson(json as Map<String, dynamic>);
    } on DioException catch (e) {
      throw Exception("Failed to load greeting: ${e.message}");
    }
  }

  Future<void> dismissGreeting(String id) async {
    try {
      final response = await dio.post("$baseUrl/api/me/greeting/$id/dismiss");
      if (response.statusCode != 204) {
        throw Exception("Failed to close greeting (${response.statusCode})");
      }
    } on DioException catch (e) {
      throw Exception("Failed to close greeting: ${e.message}");
    }
  }
}
