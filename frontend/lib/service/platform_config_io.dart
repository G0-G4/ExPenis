import "dart:io";

String get debugBaseUrl =>
    Platform.isAndroid ? "http://10.0.2.2:8000" : "http://192.168.1.5:8000";
