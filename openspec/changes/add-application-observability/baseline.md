# Preflight baseline — 2026-10-30

Измерения получены read-only по SSH с `cloud` 2026-10-30 в 15:41–15:44 UTC (18:41–18:44 Europe/Moscow). Не выполнялись deployment, ingestion тестовых данных, изменение units/flags, чтение секретов или содержимого application logs. Размеры каталогов получены отдельным `du -sb`; значения метрик/файлов могут немного расходиться из-за времени измерения.

## Host capacity

| Показатель | Значение |
| --- | --- |
| CPU | 2 logical CPUs |
| RAM total | 4 005 704 KiB |
| RAM available | 2 812 176 KiB (около 2.68 GiB) |
| Swap | 0 |
| Root filesystem | ext4, `rw,relatime,discard,errors=remount-ro` |
| Root disk total | 31 024 283 648 bytes |
| Root disk used | 18 661 261 312 bytes |
| Root disk free | 12 346 245 120 bytes (около 11.50 GiB) |

После предполагаемого дополнительного RAM budget 1 000 000 000 bytes оставалось бы около 1.75 GiB available до учёта нового backend overhead и колебаний нагрузки. После дополнительного disk budget 2 000 000 000 bytes оставалось бы около 9.64 GiB free. Это предварительный запас в одной точке времени, не подтверждение будущего peak consumption или прохождения rollout gate. На root не обнаружены quota options; изолированное принудительное ограничение новых данных ещё не настроено и не проверено.

## Existing monitoring

| Компонент | Версия | Retention | Storage baseline | Resident memory |
| --- | --- | --- | --- | --- |
| VictoriaMetrics | v1.151.0 | `-retentionPeriod="3"` (месяца) | `/var/lib/victoria-metrics-data`: 45 709 705 bytes | 105 025 536 bytes |
| VictoriaLogs | v1.52.0 | `-retentionPeriod="30d"` | `/var/lib/victoria-logs-data`: 8 192 bytes; `vl_data_size_bytes` storage/indexdb = 0 | 6 766 592 bytes |
| Grafana | 13.2.1 | N/A | Не читалась БД Grafana | Не измерена |

VictoriaMetrics слушает `127.0.0.1:8428`, VictoriaLogs — `127.0.0.1:9428`; Grafana `/api/health` сообщает `database=ok`. Из активного `/flags` VictoriaLogs не получены отдельные per-project retention или disk quota settings. Общая 30-дневная retention — фактическая действующая настройка, даже при текущем отсутствии log records в storage metrics.

Локально доступен Docker Engine 28.5.2; контейнеры spike пока не создавались.

## Design issue: shared log retention and hard disk isolation

Согласованный change требует одновременно:

1. Использовать существующий общий VictoriaLogs.
2. Целевую retention ExPenis 14 дней.
3. Изолированный дополнительный disk budget без удаления/сокращения чужой retention.

Действующий общий VictoriaLogs имеет retention 30 дней. Документированные retention и disk-space flags относятся ко всему `storageDataPath`; tenant labels не создают отдельную storage quota. Кроме того, native disk-space retention проверяется периодически и сохраняет минимум последние два дня, поэтому сам этот флаг не обеспечивает жёсткий размер. Источник: [VictoriaLogs retention and limitations](https://docs.victoriametrics.com/victorialogs/#retention-by-disk-space-usage).

Нельзя объявить 14-дневное хранение и отдельную жёсткую quota выполненными с текущей топологией только по фильтру dashboard или pre-ingestion payload count. Изменение общих flags затронет infra policy; отдельный экземпляр log storage изменит согласованную топологию и resource allocation. Поэтому до integration spike/реализации требуется явное решение пользователя и согласованное обновление design/specs/tasks.

Предлагаемый вариант: отдельный небольшой VictoriaLogs для ExPenis с 14d retention и изолированной quota-limited областью, при сохранении общих Grafana/VictoriaMetrics. Его RAM/disk входят в прежние суммарные 1 GB/2 GB; размеры Tempo/Collector перераспределяются и проверяются spike. Это предложение пока не принято и не реализовано.

Альтернатива: согласовать для ExPenis существующие 30 дней и отказаться от отдельного жёсткого log-storage cap в пользу ограниченного ingestion и мониторинга общего дискового бюджета. Это ослабление исходных требований также требует явного согласования.

## Task status

- 1.1: baseline собран и ресурсный расчёт записан; задача завершена.
- 1.2: не начата; topology зависит от решения выше.
- 1.3: не завершена; disk isolation не подтверждена, rollout gate не пройден.
- Остальные задачи не начаты; исходный backend/frontend код и серверные настройки не изменены.

## Решение пользователя после preflight

Пользователь согласовал сохранение общего VictoriaLogs с retention 30d; если общего бюджета не хватает, разрешено снижение retention всех логов до 14d. Отдельный log instance не нужен. Общие лимиты RAM/disk остаются; hard-volume и integration spike ещё предстоят. Блокирующая развилка разрешена, работа возобновлена.
