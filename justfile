# Запустить docker-compose сервисы в фоне
up:
    docker-compose up -d

# Остановить сервисы
down:
    docker-compose down

# Пересобрать образы
build:
    docker-compose build

# Перегенерировать uv.lock из pyproject.toml
lock:
    uv lock

# Сгенерировать OpenAPI спецификацию в docs/openapi.json
# Используется агентами и инструментами для генерации клиентов/скиллов.
openapi:
	uv run python generate_openapi.py

# Сгенерировать долгоживущий токен для LLM-агента (или другого сервиса).
# По умолчанию на 1 год для существующего пользователя "llm-agent".
# Пользователь должен уже существовать (создан через приложение).
# Для кастомных параметров используй:
#   just generate-agent-token --username my-agent --days 90
generate-agent-token *ARGS:
	uv run -m src.expenis.server token --username llm-agent --days 365 {{ARGS}}

# Следить за логами сервисов
logs:
    docker-compose logs -f

# Локальный backend на :8000 (DEV: CORS *, reload).
# Фронт в debug ходит сюда: http://localhost:8000
dev-backend:
    uv run -m src.expenis.server

# Flutter web debug в Chrome. Нужен уже запущенный `just dev-backend`.
dev-web:
    cd frontend && flutter run -d chrome

# Flutter web-server на :8080 без окна Chrome (Playwright / агент).
# Нужен уже запущенный `just dev-backend`.
dev-web-server:
    cd frontend && flutter run -d web-server --web-hostname 127.0.0.1 --web-port 8080

# Подсказка: два терминала для локального web
dev:
    @echo "Терминал 1: just dev-backend"
    @echo "Терминал 2: just dev-web"
    @echo "  (или just dev-web-server — UI на http://127.0.0.1:8080, без Chrome)"

# Сценарные UI-тесты Playwright (Python). Нужны уже запущенные:
#   just dev-backend
#   just dev-web-server
e2e:
    uv run --group e2e pytest e2e --browser-channel chrome -s --log-cli-level=INFO --log-cli-format="%(asctime)s %(message)s" --log-cli-date-format="%H:%M:%S"

# Собрать Flutter web-релиз в flutter_web/ (локально, не трекается)
flutter-build:
    cd frontend && flutter build web --release
    rm -rf flutter_web
    mkdir -p flutter_web
    cp -R frontend/build/web/. flutter_web/

flutter-build-android:
	cd frontend && flutter build apk --release

# Полный деплой: сборка фронта + пересборка контейнера
flutter-deploy: flutter-build
    docker-compose build frontend
    docker-compose up -d frontend

# Создать git-тег версии из pubspec.yaml (например v1.2.3) и отправить его,
# что запустит GitHub Actions workflow сборки релиза (APK + web zip).
release-tag:
    #!/usr/bin/env bash
    set -euo pipefail
    version=$(grep '^version:' frontend/pubspec.yaml | awk '{print $2}' | cut -d '+' -f1)
    echo "Creating tag v${version}"
    git tag "v${version}"
    git push origin "v${version}"

# Скачать latest web-бандл с GitHub Release и задеплоить nginx-контейнер.
# На сервере то же самое: ./deploy.sh
flutter-fetch-deploy:
    ./deploy.sh
