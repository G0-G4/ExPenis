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
```bash
just flutter-build    # собрать в flutter_web/
just flutter-deploy   # собрать + пересобрать nginx-контейнер
```