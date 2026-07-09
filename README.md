# ExPenis - Сервис для учета расходов и доходов 💰

Веб-интерфейс: [expenis.g0g4.ru](https://expenis.g0g4.ru) с авторизацией по логину/паролю

<img src="./images/ExPenis.jpg" width="256">

## Возможности
- Учет ежедневных расходов и доходов
- Категоризация транзакций
- Управление несколькими счетами
- Просмотр статистики [expenis.g0g4.ru](https://expenis.g0g4.ru)

## Структура проекта
```
├── frontend/                 # Flutter-приложение (web/iOS/Android/desktop)
│   ├── lib/                  # Dart-код
│   ├── pubspec.yaml          # Зависимости Flutter
│   └── android/ios/web/...   # Платформенные проектные файлы
├── src/expenis/
│   ├── core/                 # Основная бизнес-логика
│   │   ├── models/           # Модели базы данных
│   │   ├── service/          # Бизнес-сервисы
│   │   └── helpers.py        # Вспомогательные функции
│   ├── server/               # Веб-сервер
│   └── config.py             # Конфигурация
└── flutter_web/              # Собранный web-бандл (gitignored, через `just flutter-build`)
```
- Сервер реализован с помощью [FastApi](https://fastapi.tiangolo.com/)
- Фронтенд реализован на [Flutter](https://flutter.dev/), собранный web-бандл лежит в `flutter_web/` (не трекается, генерируется через `just flutter-build`)

## Требования
- Python 3.13+
- uv (для управления зависимостями)
- Flutter SDK (для сборки фронтенда)

## Установка
```bash
uv sync
```

## Запуск сервера
```bash
uv run -m src.expenis.server
```

## Запуск Flutter-приложения (debug)
```bash
cd frontend && flutter run
```

## Сборка и деплой web-фронтенда

### Локально (нужен Flutter SDK)
```bash
just flutter-build    # собрать в flutter_web/
just flutter-deploy   # собрать + пересобрать nginx-контейнер
```

### С сервера (без Flutter) — артефакт с GitHub Release
При релизе (`just release-tag`) CI публикует web zip в GitHub Release (в т.ч. стабильное имя `ExPenis-web.zip`).
На сервере достаточно `curl` + `unzip` (авторизация не нужна, репозиторий публичный):
```bash
just flutter-fetch-deploy   # скачать latest zip, распаковать, пересобрать nginx
```
Вручную:
```bash
curl -fsSL -o /tmp/expenis-web.zip \
  https://github.com/G0-G4/ExPenis/releases/latest/download/ExPenis-web.zip
rm -rf flutter_web && mkdir -p flutter_web
unzip -o /tmp/expenis-web.zip -d flutter_web/
docker-compose build frontend && docker-compose up -d frontend
```
