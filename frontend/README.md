# My Pennies

<img src="./images/coins.png" width="128">

Мобильное приложение для учёта личных финансов. Позволяет вести несколько счетов, записывать доходы и расходы по категориям, отслеживать остатки в
разных валютах с автоматическим пересчётом в рубли.

---

## Возможности

- **Счета** — несколько счетов с поддержкой произвольной валюты. На главном экране отображается сводный баланс в рублях и остаток в родной валюте по
  каждому счёту.
- **Транзакции** — просмотр операций за выбранный день. Навигация стрелками и выбором даты из календаря. Доходы и расходы разделены по секциям,
  внизу — дневной итог.
- **Категории** — управление категориями доходов и расходов.
- **Настройки** — профиль, смена пароля, выход (меню-гамбургер → Настройки).

---

## Стек технологий

| Компонент             | Детали                                                            |
|-----------------------|-------------------------------------------------------------------|
| Язык                  | Dart                                                              |
| Фреймворк             | Flutter, Material 3                                               |
| HTTP-клиент           | [dio](https://pub.dev/packages/dio)                               |
| Локальное хранилище   | [shared_preferences](https://pub.dev/packages/shared_preferences) |
| Форматирование чисел  | [intl](https://pub.dev/packages/intl)                             |
| Автодополнение        | [flutter_typeahead](https://pub.dev/packages/flutter_typeahead)   |
| Управление состоянием | Нет внешних библиотек — `setState` + `FutureBuilder`              |

---

## Требования

- Flutter SDK `>=3.x` (проверьте командой `flutter --version`)
- Dart SDK `^3.11.1`
- Для сборки под iOS: macOS + Xcode

---

## Установка и запуск

```sh
# Установить зависимости
flutter pub get

# Запустить в режиме отладки
flutter run

# Запустить в режиме release
flutter run --release
```

Во время работы приложения в терминале:

- `r` — горячая перезагрузка (hot reload)
- `R` — горячий перезапуск (hot restart)

---

## Сборка

```sh
flutter build apk        # Android APK
flutter build ios        # iOS (требуется macOS + Xcode)
flutter build web        # Web
```

---

## Настройка

### Авторизация

Вход и регистрация — username + password. Сервер выдаёт пару JWT (access + refresh);
клиент кладёт их в `shared_preferences` и шлёт access как `Authorization: Bearer`.
Истёкший access обновляется через `POST /api/refresh` без повторного логина.

### Бэкенд

URL бэкенда выбирается автоматически в зависимости от платформы и режима сборки:

| Режим / Платформа        | URL                       |
|--------------------------|---------------------------|
| Release (все платформы)  | `https://expenis.g0g4.ru` |
| Debug — Web              | `http://localhost:8000`   |
| Debug — Android-эмулятор | `http://10.0.2.2:8000`    |
| Debug — iOS-эмулятор     | `http://192.168.1.5:8000` |

> **Важно для iOS-симулятора:** адрес `192.168.1.5` задаётся в
> `lib/service/platform_config_io.dart` и указывает на конкретную машину разработчика.
> При запуске на другом компьютере замените его на IP вашей машины в локальной сети.

---

## Структура проекта

```
lib/
├── main.dart                  # Точка входа. MyApp + HomeScreen (PageView + NavigationBar + Drawer)
├── theme.dart                 # AppTheme — цвета, токены, ThemeData
├── models/                    # Иммутабельные модели данных
│   ├── account.dart           # Account + copyWith + fromJson/toJson
│   ├── category.dart          # Category, enum CategoryType
│   └── transaction.dart       # Transaction + TransactionCreateRequest
├── screens/                   # По одному классу на экран
│   ├── transaction_screen.dart       # Список транзакций за день
│   ├── account_screen.dart           # Список счетов с балансом
│   ├── category_screen.dart          # Список категорий
│   ├── edit_transaction_screen.dart  # Создание и редактирование транзакции
│   ├── create_account_screen.dart    # Создание счёта
│   ├── edit_account_screen.dart      # Редактирование / удаление счёта
│   ├── create_category_screen.dart   # Создание категории
│   ├── edit_category_screen.dart     # Редактирование / удаление категории
│   ├── login_screen.dart             # Вход
│   ├── register_screen.dart          # Регистрация
│   └── settings_screen.dart          # Профиль, смена пароля, выход
├── service/                   # HTTP-сервисы
│   ├── base_service.dart      # Dio, baseUrl, интерсептор авторизации
│   ├── account_service.dart   # CRUD счетов + AccountsResult + курсы валют
│   ├── category_service.dart  # CRUD категорий
│   ├── auth_service.dart      # login/register/refresh/logout/me
│   ├── transaction_service.dart  # CRUD транзакций
│   └── settings_service.dart  # Синглтон, access/refresh токены + username
├── utils/
│   └── format.dart            # formatAmount() — форматирование чисел через intl
└── widgets/                   # Переиспользуемые UI-компоненты
    ├── app_empty_state.dart   # Заглушка «пусто»
    ├── app_error_state.dart   # Заглушка «ошибка»
    ├── app_loading_spinner.dart  # Индикатор загрузки
    └── delete_dialog.dart     # Диалог подтверждения удаления
```

---

## Тесты

```sh
flutter test
```

> `test/widget_test.dart` — шаблонный файл со счётчиком, он падает. Реальные тесты:
> `app_version_test.dart`, `jwt_test.dart`, `token_refresh_interceptor_test.dart`,
> `update_service_test.dart`.

---

## Качество кода

```sh
flutter analyze   # Статический анализ (запускать перед каждым коммитом)
dart format .     # Форматирование всех Dart-файлов
```

Web-релиз на сервер (после GitHub Release): `./deploy.sh` в корне репозитория.
Подробности — в корневом `README.md` / `AGENTS.md`.
