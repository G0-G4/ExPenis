## Context

Мотивация и согласованный объём описаны в `proposal.md`; поведение — в трёх delta specs. Решения согласованы с пользователем в гриллинге по issue #15.

Backend работает под systemd за общим Caddy. В `core/logging_config.py` настроены текстовые file/console handlers, а application exception handlers и services местами записывают приватные данные. Общая БД — `playhouse.pwasyncio.AsyncSqliteDatabase`; автоматическое инструментирование синхронного sqlite нельзя считать достаточным. Во Flutter основной Dio считает 200–499 обычными ответами; refresh и retry используют отдельный Dio во избежание deadlock. Отдельные клиенты есть у проверки обновлений и версии.

По конфигурации infra на cloud уже есть VictoriaMetrics, VictoriaLogs, Grafana, blackbox_exporter и Telegram alerting. Все хранилища слушают loopback, Grafana доступна через SSH-туннель. Трассового хранилища и collector пока нет. Паспорт cloud — 2 vCPU, 4 ГБ RAM, 29 ГБ диска; фактическая загрузка, версии сервисов и retention VictoriaLogs ещё не проверены на сервере. Это обязательные проверки перед rollout, а не подтверждённая ёмкость.

## Goals / Non-Goals

**Goals:** один безопасный формат событий, минимальная связность с бизнес-кодом, корреляция клиент → API → SQLite/HTTP, ограниченный расход ресурсов и воспроизводимое provisioning.

**Non-Goals:** аудит финансовых действий, запись сессий, breadcrumbs действий пользователя, native crash dumps/Android ANR SDK, отдельная аналитическая система, изменения схемы доменной БД. Глобальные Flutter/runtime ошибки покрываются; завершение процесса ОС не гарантирует доставку.

## Decisions

### 1. Топология и владение

```text
Web / Android -- HTTPS /api/telemetry --> FastAPI allowlist + bounded queue
                       traceparent  --> business API --> SQLite / outbound HTTP
FastAPI sanitized logs + spans --> loopback OTel Collector --> VictoriaLogs / Tempo
VictoriaMetrics --> loopback backend /metrics
Grafana --> VictoriaMetrics + VictoriaLogs + Tempo --> existing Telegram contact point
blackbox_exporter --> HTTPS /api/health/ready
```

Используем Python OTel SDK/OTLP exporter, один OpenTelemetry Collector Contrib и Tempo в monolithic mode с локальным хранилищем. Версии закрепляются после проверки совместимости и ресурсов в первом этапе реализации. Backend предоставляет только ограниченный JSON ingestion; публичного OTLP proxy нет. Collector получает уже очищенные данные, дополнительно удаляет любые поля вне allowlist и отправляет логи через совместимый с закреплённой версией VictoriaLogs OTLP endpoint. Проверка этого пути входит в первый integration spike.

Общие units, collector/Tempo, datasource и включение provisioning принадлежат infra. ExPenis хранит свои scrape fragments, dashboard JSON, alert rules и инструкции подключения в `deploy/monitoring/`. При apply общие изменения выполняются как отдельная часть работы в infra с учётом её инструкций. Planning сейчас изменяет только этот change.

Альтернативы: SaaS отклонён по согласованному размещению; второй стек Grafana/metrics/logs дублировал бы infra; прямой доступ браузера к collector расширил бы недоверенный интерфейс. Локальное хранилище Tempo выбрано ради небольшого бюджета и допустимой потери диагностики. Официальная документация рекомендует object storage для production; здесь сознательно принимается отсутствие HA и долговечности диагностических данных, без добавления S3/MinIO.

### 2. Безопасный формат и существующие логи

Создать отдельный модуль наблюдаемости: фиксированные коды событий, нормализация маршрутов, sanitizer, context propagation, bounded exporters и метрики. Бизнес-сервисы используют небольшой интерфейс записи технического события/операции; DTO и HTTP остаются на transport boundary.

Не фильтровать секреты только регулярными выражениями: формировать запись из разрешённых полей. Удалить исходные чувствительные значения в местах существующего логирования, включая auth, transaction/category services, validation handlers и uvicorn access. Заменить unrestricted `exc_info`/exception messages безопасными кодами и структурированными кадрами стека: package-relative file, function, line; без locals, исходных строк, абсолютных путей и exception arguments. Не экспортировать чужие библиотечные логи по умолчанию. File/console handlers используют тот же sanitizer, а не только collector.

Маршруты — шаблоны API, неизвестный путь — `unknown`; providers — перечисление допустимых провайдеров. Ошибки имеют фиксированный code и fingerprint от code + нормализованных статических stack frames. Версии, fingerprints и trace IDs доступны в логах, но не создают неограниченных metric labels. Для метрик разрешены только небольшой каталог поддерживаемых версий или агрегат `other`; подробные client error groups вычисляются запросами к логам.

### 3. Ingestion contract

`POST /api/telemetry` принимает `application/json`, без JWT и cookie-dependent действий. В release нет общего секрета. CORS разрешает только конфигурируемые first-party web origins при необходимости; это не средство аутентификации Android и не защита от поддельных событий.

Начальные конфигурируемые ограничения: не более 16 одновременно читаемых batch, 2 секунды на чтение (408 при таймауте), 64 KiB тела до разбора JSON, 50 records на batch, 8 KiB на record, максимум 30 stack frames. Не принимать compressed bodies на этом endpoint. Время record — не старше 15 минут и не более 5 минут в будущем; метрики/алерты используют server receipt time.

Envelope: `schema_version: 1`, `platform: web|android`, `app_version` (ограниченная semver/build строка), `records`. Environment назначается конфигурацией сервера, а не произвольной клиентской строкой. Каждый record: случайный `event_id`, `kind: error|span`, `timestamp`, разрешённые поля выбранного kind; лишние поля запрещены. Error содержит controlled `code`, sanitized `frames`, необязательные trace/span/request IDs. Span содержит trace/span/parent IDs, безопасный operation, start/end, kind и controlled outcome/status. Разрешённые операции и поля являются частью DTO и генерируемой OpenAPI, не произвольным словарём attributes. Клиентские статические символы также нормализуются/ограничиваются на сервере.

Начальные rate limits: 30 batches/minute на временный источник, 300 batches/minute глобально, burst 5/20. Source IP используется только в ограниченном TTL cache rate limiter и не попадает в события/логи/метрики. Доверять forwarded source разрешено только от локального Caddy; произвольный `X-Forwarded-For` не обходит лимиты. Ограничение действует до дорогого parse/export. Схема и HTTP statuses определены в `application-telemetry/spec.md`; errors содержат код/путь поля без submitted input. Проверить отдельно Pydantic validation responses, чтобы не вернуть/залогировать запрещённые значения.

`202 {"accepted": N}` означает очередь, не сохранение. В памяти хранится bounded cache `(platform,event_id)` с TTL 15 минут, максимум 10 000 записей: повторный record в пределах окна не увеличивает счётчик ошибок; количество accepted отражает только новые records. Это best-effort дедупликация, cache не переживает restart. При переполнении cache/необходимости отклонить нагрузку используются явные capacity limits, а не бесконечный рост. Клиентские события помечены `origin=client`, их сведения недоверенные; серверные показатели нельзя перезаписать этим endpoint.

Readiness: `GET /api/health/ready`, bounded read из существующей таблицы в настроенной БД, а не только `SELECT 1`/создание новой пустой БД. Начальный timeout 1 секунда, без зависимостей от внешних курсов валют и exporter. Ответы определены в spec. Backend `/metrics` доступен scraper через loopback, не через публичный Caddy. `/api/*` уже проксируется; не добавлять публичный маршрут к `/metrics`, collector или storage.

### 4. Tracing и асинхронность

На backend использовать ASGI middleware с contextvars, безопасным именем server span и request ID на попытку. Проверять `traceparent`, не принимать baggage/tracestate и не доверять remote sampled bit для обхода sampling. Возвращать `X-Request-ID`; для явно разрешённого cross-origin dev режима раскрыть этот header в CORS. Корреляция не меняет тела бизнес-ответов.

Flutter получает небольшой transport-independent telemetry service и tracking interceptor без auth/refresh логики. На начальном этапе использовать собственную ограниченную модель completed spans, генерировать валидные W3C IDs криптографическим RNG и передавать JSON records; backend адаптирует их в OTLP spans, сохраняя trace/span/parent IDs и resource attributes. Это устраняет обязательную зависимость от зрелости Flutter OTel SDK; backend НЕ создаёт новые ID вместо присланных completed span IDs. Нужен integration test с реальным Tempo, подтверждающий parent relationships.

Один operation context охватывает исходную попытку, refresh и retry; отдельные client attempt spans являются его детьми, server spans — детьми соответствующей попытки. При coalesced refresh ожидающая операция добавляет bounded OTel span link к trace/span владельца refresh: один физический HTTP-вызов не дублируется в разные трассы. Startup refresh имеет собственный operation span. Tracking interceptor подключается и к общей Dio, и к отдельным plain Dio, не вводя повторный вход в queued auth interceptor. 4xx наблюдаются через responses, а не только `onError`. Ошибка операции учитывается один раз после завершения retry, transport spans сохраняют все попытки. Сервисный слой сообщает техническую ошибку до преобразования в пользовательский Exception; глобальные Flutter/PlatformDispatcher/zone handlers не удваивают уже отмеченный occurrence.

SQLite инструментировать в общей async точке выполнения: только operation kind, duration/outcome, без SQL, bind values и результатов. Не ограничиваться sync sqlite instrumentation. HTTPX оборачивать явными безопасными spans без автоматического capture URL/headers и без propagation во внешние домены. Flutter update/version HTTP также наблюдать с разрешёнными operation names; first-party propagation — только на явно разрешённый API origin и business routes. Не передавать context при cross-origin redirect.

Sampling по умолчанию 1.0, root operation выбирает его до первого запроса. Backend применяет собственную политику/лимиты; для наших клиентов согласованный конфигурационный rate обеспечивает связность. Изменение sampling доставляется версией/config окружения; согласованность проверяется при rollout. `/api/telemetry`, readiness и metrics исключены и из tracing, и из бизнес-HTTP метрик. In-flight business requests измеряются независимо от выборки spans.

### 5. Доставка и окружения

Начальные настройки: клиент — 200 records/1 MiB памяти, batch не более 50/64 KiB, flush раз в 5 секунд или при заполнении batch; exporter timeout 2 секунды, не более 2 повторов с jitter и учётом `Retry-After`. `400/413/415/422` не повторяются; `429/503` и сетевые сбои повторяются только в ограниченном окне. Очередь удаляет старейшие события. Закрытие вкладки или процесса может потерять последние события; persistent storage, service worker и гарантированный unload flush не требуются.

Backend log/span queues ограничены числом и байтами, initial total 8 MiB; exporter workers не блокируют HTTP event loop, timeout 2 секунды, bounded shutdown до 2 секунд. Readiness probe не ждёт exporter. Collector использует memory_limiter перед batch, ограниченные непостоянные sending queues/retry и не пишет debug payloads. Неисправность exporter отражается локальным bounded technical signal/метрикой без рекурсивной отправки ошибки.

Backend flag по умолчанию следует production окружению, frontend — release Web/Android. В debug/test нужен явный opt-in и отдельный environment; iOS/desktop остаются no-op. Version брать существующим `loadAppVersion()`, на Web не вызывать package_info plugin. Readiness остаётся доступной и при выключенной телеметрии.

### 6. Метрики, dashboard и алерты

Scrape использует существующее подключение `/etc/victoria-metrics/scrape.d/*.yml`. Основные серии: `expenis_http_requests_total`, `expenis_http_request_duration_seconds`, in-flight gauge, DB/outbound duration/errors, process metrics, ingestion accepted/rejected/dropped/export failures. Идентификаторы, клиентские timestamp/version/fingerprint не становятся неограниченными labels. Latency и ошибки 5xx вычисляются по бизнес-запросам, не по sampling и не по клиентским reports.

Dashboard показывает перечисленное в monitoring spec, группирует клиентские errors запросом к VictoriaLogs, использует trace IDs для переходов в Tempo и обратный переход с trace к логам. Если Flutter release stack обфусцирован/минифицирован, grouping использует стабильный code и доступные символы; читаемость исходного Dart стека не обещается без сохранённых symbol artifacts. Не публиковать sourcemaps с приватными исходниками автоматически.

Backend alert: за 5 минут `increase(5xx) >= 5` И `increase(5xx)/increase(all business responses) >= 0.20`, при положительном знаменателе; без дополнительной 5-минутной выдержки после выполнения условия. Readiness: blackbox failure `for: 3m`. Client: минимум 3 различных occurrence одной группы за 10 минут по server receipt time, отдельное alert instance на fingerprint/platform/version. Count и группировка берутся из VictoriaLogs, не высококардинальных counters. Проверить поддержку Grafana datasource alert evaluation в закреплённой версии. Pending/no-data не считается recovery; повтор и recovery используют существующую policy infra. Количество отображаемых/оцениваемых групп ограничивается для защиты от client spoofing.

### 7. Retention и лимиты — обязательный rollout gate

Использовать десятичные лимиты: 1 000 000 000 bytes RAM и 2 000 000 000 bytes дополнительного диска. Начальное распределение RAM новых services: Tempo 640 MiB, Collector 160 MiB, guard/helper 32 MiB; общий systemd slice имеет MemoryMax не выше 1 GB. Прирост backend памяти измеряется отдельно и учитывается в проверке запаса хоста. Не включать тяжёлые trace metrics-generator/service graph компоненты по умолчанию.

Дисковый план: до 0.4 GB trace store вместе с WAL/temp, 0.4 GB дополнительного log storage, 0.35 GB metric growth, 0.85 GB binaries/plugin/остальные файлы. Сумма включает local logs/journal, queue/temp и запас compaction, а не только экспортированные payload bytes. Для новых trace directories использовать отдельную quota-limited область; ошибки записи не влияют на API. Guard прекращает новый приём до исчерпания запаса и запускает только поддерживаемое удаление старых trace data; произвольное удаление активных WAL/blocks запрещено. Если безопасная очистка требует остановки/сброса только нового trace store, допустима потеря всех его диагностических данных, с остановкой writer и сохранением domain data.

VictoriaLogs остаётся общим сервисом. После preflight пользователь явно согласовал общую retention 30d с возможностью снизить её до 14d для всех источников, если бюджет не выдерживается. Не добавлять отдельный экземпляр. Его storage размещается в выделенной ограниченной области до 0.4 GB; native disk retention настроить ниже hard capacity с запасом на два последних дня и compaction. Проверить суммарную нагрузку всех log sources в spike; native soft cap сам по себе не является hard quota. Данные в общем storage при переполнении могут истекать раньше. Настройки общих metrics/trace retention этим решением не меняются. До переноса storage нужен отдельный проверенный migration/rollback; сейчас shared storage содержит 8 KiB и ноль записей по storage metrics.

На ext4 cloud нет активных quota options. Для новых trace/log directories использовать отдельные fixed-size loopback ext4 filesystems с systemd mount dependencies (или существующие эквивалентные hard quotas, если они появились к rollout). Создать hard-cap volumes 0.4 GB trace и 0.4 GB shared logs, оставить 1.2 GB на metrics/binaries/plugin/прочий дополнительный расход. При заполнении тома exporters отказывают/теряют данные, но не расширяют volume. Проверить restart, cleanup и backpressure в изолированном Linux Docker spike до изменения сервера. Shared VictoriaMetrics остаётся на прежнем volume: каталог series и admission budget ограничивают добавленные ряды; объём его прироста и вспомогательных файлов проверяется отдельно.

Для metrics сохраняется существующая 3-месячная retention; ограничить каталог labels/series, частоту scrape и измерить прирост. Все размеры и resource enforcement проверить нагрузкой с отказами/compaction до production. Если 100% tracing не помещается, не уменьшать sampling автоматически: явно пересмотреть конфигурацию в пределах согласованного бюджета.

## Risks / Trade-offs

- [Небольшой общий cloud не вмещает новые services] → сначала resource/compatibility spike и gate; без автоматического увеличения лимитов или production rollout при провале.
- [Общий log budget затрагивает все источники] → согласованная общая политика 30d, fallback 14d, soft cap ниже hard capacity и проверка суммарной нагрузки; не менять metrics/trace policy других проектов.
- [Локальный Tempo не даёт рекомендованной production durability] → диагностические данные считаются теряемыми; исключены HA/object storage и резервирование телеметрии.
- [Недоверенный публичный ingestion позволяет подделывать ошибки] → схемы, rate/body/global limits, bounded caches/groups, source separation; алерты клиентских ошибок не доказывают отказ backend.
- [SDK автоматически собирает SQL/URL/exception details] → явное ограниченное инструментирование, deny-by-default export и privacy tests на всех sinks.
- [Дедупликация, in-memory queues, restart или shutdown теряют события] → best-effort контракт, отсутствие crash-free-rate обещаний, отдельные drop/export health сигналы.
- [Повторное вмешательство в refresh ломает auth] → самостоятельный tracking interceptor на plain Dio и regression test refresh/retry без deadlock.
- [Sampling/потеря клиентского batch оставляют server spans без родителей] → не объявлять трассы полными при отсутствии spans; тестировать корректность ID, не гарантировать доставку.

## Migration Plan

1. Проверить зависимости, exporter/datasource compatibility и реальные ресурсы; зафиксировать версии, baseline и quota enforcement. При провале gate не развёртывать.
2. Реализовать безопасное логирование и privacy tests до включения remote export; затем backend APIs, метрики и tracing. Изменения доменной схемы/SQL migrations не нужны.
3. Реализовать Web/Android collection с выключением через config, совместимую с уже установленными клиентами без trace headers. Backend выпустить раньше клиентов.
4. Подготовить provisioning в ExPenis и общие infra изменения, проверить Caddy/units/datasources/queries в изолированном окружении. Не менять backup pipeline.
5. Выполнить controlled rollout и Web/Android smoke, synthetic privacy checks, DB failure, exporter outage, alert/recovery и resource tests. Не вызывать реальные финансовые изменения для проверки ошибок.
6. Rollback: выключить flags, остановить только новые exporter/collector/Tempo services, убрать только новый scrape/dashboard/alert provisioning; сохранить существующий infra. Откат frontend/backend не требует domain migrations.

## References

- Локальные факты: `docs/deployment.md`, `frontend/AGENTS.md`, `src/expenis/core/logging_config.py`, `src/expenis/server/application.py`; infra `servers/cloud.md`, `monitoring/README.md`, `monitoring/cloud/grafana/alerting/`.
- [Tempo deployment modes](https://grafana.com/docs/tempo/latest/reference-tempo-architecture/deployment-modes/) и [Linux deployment](https://grafana.com/docs/tempo/latest/set-up-for-tracing/setup-tempo/deploy/locally/linux/): monolithic mode; local storage ориентировано на evaluation/dev, production recommendation — object storage.
- [VictoriaLogs retention, disk limits and deletion](https://docs.victoriametrics.com/victorialogs/): общий характер retention/partition lifecycle и ограничения регулярного удаления.
- [OpenTelemetry Collector configuration](https://opentelemetry.io/docs/collector/configuration/): memory limiter, bounded batching/queues и exporter configuration.
