# AGENTS.md

Guidance for agentic coding agents working in this Flutter expense tracking app.

---

## Commands

### Development

```sh
flutter run                  # Run in debug mode
flutter run --release        # Run in release mode
# Press 'r' to hot-reload, 'R' to hot-restart in the terminal
```

### Code Quality

```sh
flutter analyze              # Static analysis (run before every commit)
dart format .                # Format all Dart files (enforced style)
dart format --output=show .  # Preview formatting changes without writing
```

### Testing

```sh
flutter test                              # Run all tests
flutter test test/widget_test.dart        # Run a single test file
flutter test --name "widget name"         # Run tests matching a name pattern
flutter test --tags smoke                 # Run tests by tag
```

> Note: `test/widget_test.dart` is boilerplate and currently fails because it
> references a counter widget that no longer exists. Update or replace it when
> adding real tests.

### Dependencies & Build

```sh
flutter pub get              # Install dependencies
flutter pub upgrade          # Upgrade to latest compatible versions
flutter clean                # Clean build artifacts and caches

flutter build apk            # Android APK
flutter build ios            # iOS (requires macOS + Xcode)
flutter build web            # Web

just release-tag             # Tag vX.Y.Z from pubspec and push (triggers release CI: APK + web zip)
just flutter-fetch-deploy    # Server: curl latest ExPenis-web.zip, unpack, restart nginx
```



---

## Architecture

```
lib/
├── main.dart                  # App entry point, HomeScreen with PageView nav
├── theme.dart                 # AppTheme — design tokens, ThemeData
├── models/                    # Immutable data models
│   ├── account.dart
│   ├── category.dart
│   └── transaction.dart       # Also contains TransactionCreateRequest
├── screens/                   # UI screens (one class per file)
│   ├── account_screen.dart
│   ├── transaction_screen.dart       # TransactionScreen (main list)
│   ├── category_screen.dart
│   ├── create_account_screen.dart
│   ├── create_category_screen.dart
│   ├── edit_account_screen.dart
│   ├── edit_category_screen.dart
│   ├── edit_transaction_screen.dart  # Handles both create and edit
│   ├── settings_screen.dart          # Account profile, change password entry, logout
│   ├── login_screen.dart             # Login by username + password
│   ├── register_screen.dart          # Registration by username + password
│   └── change_password_screen.dart   # Change current account password
├── service/                   # HTTP service layer
│   ├── base_service.dart      # Dio setup, baseUrl resolution, auth interceptor (Bearer + auto-refresh on 401)
│   ├── account_service.dart   # Also contains AccountsResult helper class
│   ├── category_service.dart
│   ├── auth_service.dart      # login/register/refresh/logout/me/changePassword
│   ├── navigator_service.dart # Global GlobalKey<NavigatorState> for auth-gate redirects
│   ├── settings_service.dart  # Singleton, uses shared_preferences (access/refresh tokens + username)
│   ├── transaction_service.dart
│   └── update_service.dart    # GitHub release check + APK download/install (auto-update)
├── utils/
│   └── format.dart            # formatAmount() — number formatting via intl
└── widgets/                   # Shared UI components
    ├── app_empty_state.dart
    ├── app_error_state.dart
    ├── app_loading_spinner.dart
    ├── delete_dialog.dart
    └── update_dialog.dart       # "Update available" prompt with APK download progress
```

### Navigation

- App entry uses `MaterialApp.routes` with named routes: `/boot` (auth gate),
  `/login`, `/register`, `/home`, `/settings`, `/change-password`.
- `_AuthGate` (in `main.dart`) checks `SettingsService.hasAccessToken()` at
  startup and `pushReplacementNamed` to either `/login` or `/home`.
- `MaterialApp.navigatorKey` is `appNavigatorKey` (see `navigator_service.dart`)
  so the auth interceptor can force-redirect to `/login` when the refresh token
  is dead (see Auth section).
- `HomeScreen` uses a `PageView` + `NavigationBar` (Material 3) with **3 tabs**.
- Default tab index is **1** (Transactions).
- Tab order: Accounts (0), Transactions (1), Categories (2).
- **Settings** is not a tab — it is accessed via a `Drawer` (hamburger icon in
  the `AppBar`) that pushes `/settings` via `Navigator.pushNamed`.
- Page swiping is disabled (`NeverScrollableScrollPhysics`); use `animateToPage`.
- Sub-screens use `Navigator.push` with `MaterialPageRoute` (resource CRUD) or
  named routes (auth / settings branches).

### Platform Base URLs

Resolved in `BaseService.baseUrl`:

- **Release**: `https://expenis.g0g4.ru`
- **Web (debug)**: `http://localhost:8000`
- **Android emulator (debug)**: `http://10.0.2.2:8000`
- **iOS simulator (debug)**: `http://192.168.1.5:8000`

### Auto-Update

- On startup in release mode (`kReleaseMode`), `_AuthGate` in `main.dart` calls
  `UpdateService().checkForUpdate()` and shows `UpdateDialog` via
  `showUpdateDialog()` if a newer GitHub release exists.
- Version comparisons use `UpdateService.compareSemver(a, b)` in
  `lib/service/update_service.dart`. Version source is `pubspec.yaml`,
  read via `package_info_plus`.
- On Android, the APK is downloaded to the temp dir and installed via a
  MethodChannel `expenis/installer` (`installApk(path)`) implemented in
  `MainActivity.kt`. Requires `REQUEST_INSTALL_PACKAGES` permission and a
  `FileProvider` (`${applicationId}.fileprovider`, `res/xml/file_paths.xml`).
- Non-Android: the dialog opens the release `html_url` via `url_launcher`.
- Releases are created by pushing a git tag `vX.Y.Z` matching the version in
  `pubspec.yaml`; CI attaches APK plus web zips (`ExPenis-X.Y.Z-web.zip` and
  stable `ExPenis-web.zip` for curl latest download).
  See root `AGENTS.md` → "Releases and app auto-update".


### State Management

No external state management library. Use `setState` + `FutureBuilder<T>` for
all async data loading. Do not introduce Provider, Riverpod, or Bloc without
team agreement.

---

## Code Style

### Formatting

- Indentation: **2 spaces** (Dart standard).
- Run `dart format .` before committing. The CI equivalent is `flutter analyze`.
- Line length: default (80 chars); `dart format` handles wrapping automatically.

### Strings

- Use **double quotes** for all Dart string literals: `"hello"`, not `'hello'`.
- The `prefer_single_quotes` lint rule is explicitly disabled in
  `analysis_options.yaml`.

### Imports

- Order: `dart:` core libs → `package:flutter/` → `package:` third-party →
  `package:expenis_mobile/` local. Separate groups with a blank line.
- Always use the full package path for local imports:
  ```dart
  import 'package:expenis_mobile/models/transaction.dart';
  ```
  Never use relative paths like `../models/transaction.dart`.

### Naming Conventions

| Entity                     | Style        | Example                         |
|----------------------------|--------------|---------------------------------|
| Classes, enums, typedefs   | `PascalCase` | `TransactionService`            |
| Variables, methods, params | `camelCase`  | `fetchTransactions`             |
| Private members            | `_camelCase` | `_formKey`, `_fetchData()`      |
| Constants                  | `camelCase`  | `baseUrl` (not SCREAMING_SNAKE) |
| Files                      | `snake_case` | `account_service.dart`          |
| Enum values                | `camelCase`  | `CategoryType.income`           |

### Classes and Constructors

- Prefer `const` constructors wherever all fields are `final` and compile-time
  constant.
- Use the `super.key` shorthand (not `Key? key` + `super(key: key)`):
  ```dart
  const MyWidget({super.key});
  ```
- Use named parameters with `required` for all non-optional fields.
- Widget constructors must always accept `Key? key` via `super.key`.

### Models

- All model fields are `final` (immutable).
- Provide a `factory ClassName.fromJson(Map<String, dynamic> json)` constructor.
- Provide a `Map<String, dynamic> toJson()` method when the model is sent to API.
- Provide `copyWith` for models that need partial updates (see `Transaction` and
  `Account`; `Category` intentionally omits it).
- Use enums for categorical string fields (e.g., `CategoryType`, `TransactionType`).
- `TransactionCreateRequest` (in `transaction.dart`) is the write DTO used for
  both creating and updating transactions. It carries `accountId`, `categoryId`,
  `amount`, optional `description`, and optional `createdAt`.
- `AccountsResult` (in `account_service.dart`) is a helper class returned by
  `AccountService.fetchAccounts()` that pairs `List<Account> accounts` with
  `double totalAmountRubles`.

### Widgets and State

- Extend `StatelessWidget` for widgets with no mutable state.
- Extend `StatefulWidget` + `State<T>` when local state is needed.
- Use `FutureBuilder<T>` for async data; always handle all `ConnectionState`
  cases and display loading indicators / error messages.
- When smooth re-loading without full tree rebuild is needed (e.g. switching
  date ranges in `TransactionScreen`), use a manual `setState`-based pattern
  with `_isLoading` / `_loadError` boolean flags instead of `FutureBuilder`.
- Dispose controllers and other resources in `dispose()`.
- Instantiate services directly in widget state — no dependency injection:
  ```dart
  final _service = TransactionService();
  ```

### Services

- All API services extend `BaseService` and use the inherited `dio` getter.
- Follow the CRUD URL pattern: `$baseUrl/api/<resource>` and
  `$baseUrl/api/<resource>/<id>`.
- Wrap every Dio call in `try/on DioException catch`:
  ```dart
  try {
    final response = await dio.get('$baseUrl/api/transactions');
    return (response.data as List).map((e) => Transaction.fromJson(e)).toList();
  } on DioException catch (e) {
    throw Exception('Failed to fetch transactions: ${e.message}');
  }
  ```
- Services must not contain UI code or reference `BuildContext`.

### Error Handling

- Services re-throw as `Exception(descriptive message)` — never swallow errors.
- Screens catch service exceptions and display a `SnackBar`:
  ```dart
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(content: Text('Error: $e')),
  );
  ```
- Never use `print()` for errors in production code (`avoid_print` lint).

### Navigation

- Push sub-screens with `Navigator.push<T>` and `MaterialPageRoute`.
- Return results to the caller via `Navigator.pop(context, result)`.
- Check `mounted` before using `context` after any `await`:
  ```dart
  if (!mounted) return;
  Navigator.pop(context);
  ```

---

## Backend API Reference

| Method           | Path                          | Description                                       |
|------------------|-------------------------------|---------------------------------------------------|
| `POST`           | `/api/register`               | Register by username + password → `AuthResponse`  |
| `POST`           | `/api/login`                  | Login by username + password → `AuthResponse`      |
| `POST`           | `/api/refresh`                | Issue new token pair using the refresh token       |
| `POST`           | `/api/logout`                 | Unset auth cookies server-side (no-op for bearer)  |
| `GET`            | `/api/me`                     | Current user profile (`{id, username, telegram_id}`) |
| `PUT`            | `/api/me/password`            | Change password (`{old_password, new_password}`)    |
| `GET`            | `/api/transactions`           | List transactions (`date_from`, `date_to` params) |
| `POST`           | `/api/transactions`           | Create transaction                                |
| `GET`            | `/api/transactions/{id}`      | Get transaction                                   |
| `PUT`            | `/api/transactions/{id}`      | Update transaction                                |
| `DELETE`         | `/api/transactions/{id}`      | Delete transaction                                |
| `GET`            | `/api/accounts`               | List accounts (returns `{ accounts, total_amount_rubles }`) |
| `POST`           | `/api/accounts/account`       | Create account                                    |
| `GET`            | `/api/accounts/account/{id}`  | Get account                                       |
| `PUT`            | `/api/accounts/account/{id}`  | Update account                                    |
| `DELETE`         | `/api/accounts/account/{id}`  | Delete account                                    |
| `GET`            | `/api/currency/codes`         | List available currency codes                     |
| `GET/POST`       | `/api/categories`             | Categories CRUD                                   |
| `GET/PUT/DELETE` | `/api/categories/{id}`        | Individual category ops                           |

- Date params use `yyyy-MM-dd` format.
- Authentication: JWT pair (access + refresh) issued by `/api/login` or
  `/api/register`. The access token is sent as `Authorization: Bearer <token>`
  on every authenticated request. Tokens are stored in `SettingsService`
  (singleton, `shared_preferences`): keys `access_token`, `refresh_token`,
  `username`.
- `BaseService` uses a `QueuedInterceptorsWrapper`. On `401` it transparently
  calls `AuthService.refresh()` using the stored refresh token, persists the
  new pair, and retries the original request once (guarded by
  `requestOptions.extra["retried"]`). If refresh fails, it clears auth state
  and pushes `/login` via `appNavigatorKey`. Requests that set their own
  `Authorization` header (refresh, logout, me, changePassword) mark
  `Options.extra["skipAuth"] = true` so the interceptor doesn't overwrite it.
- Password rules: minimum 6 characters, maximum 72 bytes (bcrypt limit).
  Enforced both server-side and in the register/change-password forms.
- Dio is configured with `validateStatus` accepting all responses with status
  200–499 as non-exceptions. Services must check `response.statusCode` manually
  for non-200 responses rather than relying on Dio to throw.
