class PersonalGreeting {
  final String id;
  final String text;
  final DateTime? expiresAt;

  const PersonalGreeting({
    required this.id,
    required this.text,
    required this.expiresAt,
  });

  factory PersonalGreeting.fromJson(Map<String, dynamic> json) {
    return PersonalGreeting(
      id: json["id"] as String,
      text: json["text"] as String,
      expiresAt: json["expires_at"] == null
          ? null
          : DateTime.parse(json["expires_at"] as String).toUtc(),
    );
  }
}
