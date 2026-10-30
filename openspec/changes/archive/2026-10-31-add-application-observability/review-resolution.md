# Разбор grok-review-efca9026 — 31 октября 2026

| Пункт | Решение |
| --- | --- |
| 1. Route в логах | Исправлено: событие использует шаблон matched route из ASGI scope. Проверены local JSON и OTLP, без значений path/query. |
| 2. Необработанные исключения | Исправлено: общий scoped logger проходит через SafeFormatter; middleware и внешний handler не дублируют событие. Проверены обычные/excluded endpoints, disabled mode и ошибка после начала streaming response. |
| 3. Token buckets | Исправлено: отклонение сохраняет дробный остаток; source throttle/capacity не расходуют global tokens, global denial не расходует source tokens. |
| 4. Конфигурация | Чтение трёх документированных knobs уже присутствовало. Добавлен безопасный fallback: неверные URL/числа отключают сбор, бизнес-API продолжает работать. При старте — один локальный фиксированный warning без значений конфигурации. |
| 5. Локальные файлы | Добавлены ignore rules для data, потенциального signing blob, IDE, screenshots и Playwright snapshots. Проверено отсутствие этих путей среди tracked files. Пользовательские файлы не читались, не удалялись и не изменялись; утверждение об утечке ключа не делается. |
| 6. Ответы провайдера | Принято: любой non-2xx помечает dependency span/метрику как error. Проверены 200/302/429/503, sampling 0/1 и отсутствие propagation/секретов. |
| 7. Невалидный span в batch | Принята локальная защита от backwards clock и длительности >15 минут до batching. Partial-ingestion/retries на 422 не вводились: это изменило бы утверждённый all-or-nothing контракт и terminal 422 policy. Дополнительно исправлен повтор terminal responses, если переданный Dio бросает DioException вместо возврата response. |

Для пункта 7 доставка остаётся best effort: другие причины schema rejection,
включая рассинхронизацию с серверными часами, по-прежнему могут отклонить весь
batch. Локальная проверка времени не является синхронизацией часов или гарантией
доставки crash reports. Неизвестные поля и недопустимые данные сервер не принимает.

## Проверки

- Полный backend suite: 106 passed, 8 warnings.
- Полный Flutter suite: 60 passed; analyze — no issues.
- Mypy observability/logging: no issues in 8 source files.
- Полный `mypy src`: прежние 10 ошибок missing Peewee stubs / duplicate packages;
  новых ошибок в проверенном модуле нет.
- Gitignore подтверждён через `git check-ignore`; private paths не tracked.
- API schemas/statuses не менялись; OpenSpec остаётся 30/31, выпуск не запускался.

Выводы native resource acceptance относятся к предыдущему изолированному запуску.
Исправления после ревью проверены локальными regression/integration tests; новый
cloud rollout или повторное развёртывание стенда в этом проходе не выполнялись.
