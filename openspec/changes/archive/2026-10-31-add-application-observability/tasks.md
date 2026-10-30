## 1. Совместимость и ресурсный gate

- [x] 1.1 Проверить реальные версии, свободные ресурсы cloud, retention и storage layout VictoriaLogs/VictoriaMetrics; сохранить baseline и расчёт дополнительных RAM/disk в deployment notes, не читая и не публикуя секреты. Проверка: отчёт с датой и измерениями, сравнением с 1 GB RAM/2 GB disk и сохранением чужой retention. Результат: `baseline.md`, выявлено требующее согласования несоответствие общей retention 30d и отдельного disk budget.
- [x] 1.2 Выполнить изолированный integration spike Python OTLP → Collector → VictoriaLogs/Tempo и Grafana query/alert evaluation; закрепить совместимые версии. Проверка: тестовая очищенная запись и trace с заданными IDs читаются, VictoriaLogs query доступен Grafana Alerting, конфиги проходят validators выбранных версий.
- [x] 1.3 Подтвердить исполнимые disk quotas/admission guard, безопасную очистку нового trace store и учёт прироста shared storage/local logs. Проверка: ограниченный тест переполнения/compaction удерживает суммарные пределы без удаления чужих данных; при провале gate зафиксировать необходимость пересмотра и не переходить к rollout.

## 2. Безопасная телеметрия backend

- [x] 2.1 Добавить минимальный модуль наблюдаемости, конфигурацию окружения, controlled event codes и sanitizer allowlist; добавить только обоснованные OTel/metrics зависимости через uv. Проверка: `uv sync` и целевые тесты разрешённых полей, ограничений строк/frames и disabled mode проходят.
- [x] 2.2 Очистить существующие application/service/uvicorn/dependency logging sinks, устранить дубли JWT/validation handlers, исключить unrestricted exception text/locals. Проверка: privacy tests захватывают file/console/export записи auth, DTO validation, account/category/transaction и не находят подставленные токены, суммы, названия, IP, query strings и submitted values.
- [x] 2.3 Реализовать contextvars/ASGI request context и безопасную корреляцию с `X-Request-ID`, совместимую со старыми клиентами. Проверка: concurrent-request tests не смешивают IDs; отсутствующий/испорченный `traceparent` создаёт новый контекст без изменения бизнес-ответа.
- [x] 2.4 Реализовать bounded async log/span queues, короткие timeout/retry/shutdown и drop/export-failure counters. Проверка: тест недоступного exporter и переполнения подтверждает границы памяти, отсутствие блокировки event loop и рекурсивной телеметрии.

## 3. API приёма, readiness и метрики

- [x] 3.1 Добавить versioned telemetry DTO и `POST /api/telemetry` с allowlist errors/spans, валидацией IDs/time/size и безопасными validation responses. Проверка: целевые API tests покрывают `202/204/400/413/415/422`, отсутствие auth requirement и отсутствие submitted values в ошибках/логах.
- [x] 3.2 Добавить pre-parse source/global limits, bounded TTL event deduplication, доверие forwarded source только локальному proxy и capacity rejection. Проверка: tests покрывают `429/503`, `Retry-After`, spoofed headers, retries одного event ID и исчерпание bounded caches без роста памяти.
- [x] 3.3 Реализовать преобразование завершённых client spans в OTLP с сохранением trace/span/parent IDs и отделением client origin от server origin. Проверка: integration test связывает присланный client span с server span в Tempo и не допускает произвольных attributes/перезаписи серверных метрик.
- [x] 3.4 Добавить `GET /api/health/ready` с bounded чтением существующей таблицы SQLite. Проверка: tests успешного чтения, отсутствующей/недоступной БД и timeout возвращают точные `200/503` bodies, без записи domain data; отказ exporter не портит readiness.
- [x] 3.5 Добавить loopback `/metrics`: business HTTP counters/histograms/in-flight, dependency/process/readiness и delivery metrics. Проверка: tests статусов/параллельных запросов/unknown routes подтверждают bounded labels, исключение telemetry/health/scrape и независимость counts от trace sampling; публичный Caddy не проксирует endpoint.
- [x] 3.6 Описать новые routes/DTO, response headers, auth policy, лимиты и error examples в исходных FastAPI decorators; повысить backend version и выполнить `just openapi`. Проверка: `docs/openapi.json` отражает контракт и version, старые business schemas/operation IDs сохранены.

## 4. Трассировка backend и зависимостей

- [x] 4.1 Реализовать server spans и собственную sampling policy с default 1.0 и исключениями служебных endpoints. Проверка: tests валидного/испорченного контекста, sampled bit и rates 0/1 подтверждают правила spec и отсутствие recursive tracing.
- [x] 4.2 Инструментировать общую async SQLite execution boundary без capture SQL/parameters/results. Проверка: async integration tests реального чтения/записи/ошибки показывают child spans и durations без тестовых приватных значений и сохраняют транзакционное поведение.
- [x] 4.3 Инструментировать исходящий httpx в exchange-rate dependencies безопасными именами. Проверка: mocked-provider tests success/error/redirect показывают parent spans и отсутствие trace/baggage headers во внешних запросах, URL query/keys/body в output.

## 5. Flutter Web и Android

- [x] 5.1 Добавить transport-independent telemetry service: config/version/platform, W3C ID generation, records, bounded memory queue, batching/retry и no-op режимы. Проверка: Flutter tests лимитов/очереди/retry/disabled и Web version loading проходят; на iOS/desktop automatic export отсутствует.
- [x] 5.2 Подключить tracking к общей и plain Dio с operation context, отдельными attempt spans и обработкой response statuses 200–499. Проверка: Flutter regression tests сценариев initial 401 → refresh → retry, refresh failure и business login 401 сохраняют причинность без deadlock, лишних запросов или технических алертов для ожидаемого отказа.
- [x] 5.3 Подключить глобальные Flutter/PlatformDispatcher/zone handlers и reporting обработанных технических ошибок services, сохранив существующее отображение пользователю. Проверка: одна искусственная ошибка через несколько обработчиков даёт один occurrence, а response.data/exception arguments не попадают в records.
- [x] 5.4 Покрыть технические update/version network operations и first-party-only propagation, исключить telemetry transport из инструментирования/auth refresh. Проверка: tests внешних origin/redirect/telemetry delivery не обнаруживают утечку tracing headers, recursion и capture URL/body.
- [x] 5.5 Проверить release Web и Android compilation, `flutter analyze`, форматирование затронутых файлов и целевые `flutter test`. Проверка: сборки проходят, no-op unsupported platforms не требуют новых native plugins, результаты и существующие unrelated failures записаны.

## 6. Provisioning приложения и общая infra

- [x] 6.1 Добавить `deploy/monitoring/` с project scrape fragment и dashboard JSON: availability/readiness, HTTP rate/errors/latency, dependencies/process, client groups и delivery health. Проверка: JSON/config validators и временный Grafana import показывают правильные environment filters, zero traffic и отдельное no-data состояние.
- [x] 6.2 Добавить project alert rules с согласованными 3m readiness, 5xx ≥5 и ≥20%/5m, client ≥3/10m; подключить существующую Telegram policy. Проверка: controlled evaluation покрывает 5/25 против 5/26 и 4/20, single/duplicate client errors, grouping/version/platform, recovery и отсутствие production alerts из dev.
- [x] 6.3 Подготовить в infra systemd units/slice для Collector/Tempo, loopback-only endpoints, datasource и подключение project provisioning, quota/admission/retention settings. Проверка: validators, port inventory, effective MemoryMax и disk enforcement соответствуют design; существующие backup/monitoring rules не изменены по смыслу.
- [x] 6.4 Настроить Grafana log→trace и trace→logs links с постоянными datasource UIDs и environment filters. Проверка: один retained test trace открывает свои sanitized logs и обратно; expired/missing spans не отображаются как полная трасса.
- [x] 6.5 Обновить deployment/runbook в ExPenis и соответствующие infra notes: flags, sampling, thresholds, retention, лимиты, безопасная очистка и rollback. Проверка: инструкции воспроизводимы, не содержат секретов, не дублируют бэкапы и явно описывают best-effort delivery/локальное Tempo storage.

## 7. Сквозная проверка и готовность к rollout

- [x] 7.1 Прогнать целевые backend tests, затем `uv run pytest` и `uv run mypy src` для общего middleware/logging/DB instrumentation; выполнить Flutter checks из 5.5. Проверка: результаты записаны, новые failures устранены, базовые unrelated проблемы явно отделены.
- [x] 7.2 Проверить Web и Android end-to-end: обычный запрос → SQLite, refresh/retry, controlled handled/unhandled error, корреляция и dashboard. Проверка: сохранены обезличенные trace IDs/screenshots с правильным parent tree и одним error occurrence, production финансовые данные не менялись ради теста.
- [x] 7.3 Проверить DB outage и exporter/collector outage, overflow/rate limits, shutdown/restart и невалидный ingestion под нагрузкой. Проверка: business behavior сохраняется кроме реального отказа DB, очереди/ресурсы ограничены, readiness и no-data верны, telemetry не содержит privacy canaries.
- [x] 7.4 В изолированном окружении подтвердить Telegram firing/grouping/recovery и ресурсный профиль с compaction/retention, затем повторно проверить запас cloud до rollout. Проверка: acceptance report с измерениями подтверждает 1 GB RAM/2 GB дополнительного диска и отсутствие воздействия на чужие данные; при провале rollout не выполняется.
- [x] 7.5 Подготовить выпуск и controlled rollout backend раньше Web/Android по repository release/deployment workflow; выполнить его только в рамках отдельного запроса на реализацию/развёртывание. Проверка: до запуска доступны release notes/version changes по правилам репозитория, rollback проверен, после запуска smoke/alerts/resources подтверждены; текущий planning turn ничего не публикует.
