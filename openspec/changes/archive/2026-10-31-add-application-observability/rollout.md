# Rollout — 31 октября 2026 (Europe/Moscow)

- Выпущен [v1.2.1](https://github.com/G0-G4/ExPenis/releases/tag/v1.2.1),
  frontend 1.2.1+11, backend API 1.2.0; release code commit `bc7482e`.
- v1.2.0 отменён до публикации. Новый тег создан после удаления одноразовых
  helpers, временных конфигов и сырых отчётов. История не переписывалась.
- Infra commits: `f8266e4`, cleanup bytecode `3942992`. Секреты/локальные БД
  в commits не включались; пользовательские файлы сохранены.
- Установлены ограниченные Collector/Tempo/guard и два ext4 storage по 400 MB;
  общий VictoriaLogs сохраняет 30d, metrics — 3 месяца, traces — 7d.
- Backend обновлён перед Web. На серверном Python 3.14.2 прошли 106 тестов
  с отдельной временной SQLite; рабочая БД не использовалась тестами.
- Подключены datasource logs/traces, dashboard ExPenis (15 панелей), четыре
  production alert rules и существующая Telegram policy. В Grafana 13 dashboard
  проверен в resource backend, legacy dashboard table не используется.
- Public readiness: 200; backend scrape `up=1`; readiness `probe_success=1`.
  Проверены anonymous ingestion validation и log/trace correlation:
  `50a6b14a7d4244c0acd63f41b51f0f68` (без финансовых операций).
- Web развёрнут через `deploy.sh`: version.json 1.2.1/build 11. Headless Chrome:
  Login виден, page errors 0, telemetry response 202.
- APK: SHA-256 совпал с GitHub asset digest, package `ru.g0g4.expenis`,
  versionCode 11/versionName 1.2.1, Android v2 signature verified.
  Установка release APK на пользовательский телефон не выполнялась.
- Core slice MemoryMax 1 GB, наблюдаемый MemoryCurrent около 268 MB;
  guard success, collection allowed. Host MemAvailable около 2.06 GB,
  free disk около 10.76 GB. Root+binary storage около 1.43 GB плюс учтённый
  guard прирост зависимостей/metrics/journal, ниже согласованного бюджета.
- Для отката сохранены исходный log store `/var/lib/victoria-logs-data`,
  plugin rollback и metadata в `/var/lib/expenis-observability`; исходный
  backend commit `c0357cc` доступен. Рабочий rollback не запускался при
  успешной проверке. Бэкапы и Caddy-конфигурация не менялись.

OpenSpec: 31/31. Одноразовые deployment/smoke scripts, APK и screenshots
находятся вне checkout и не коммитились.
