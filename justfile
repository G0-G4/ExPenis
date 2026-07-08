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

# Следить за логами сервисов
logs:
    docker-compose logs -f

# Собрать Flutter web-релиз из sibling-репозитория и скопировать в flutter_web/
flutter-build:
    cd ../expenis-mobile/expenis_mobile && flutter build web --release
    rm -rf flutter_web
    mkdir -p flutter_web
    cp -R ../expenis-mobile/expenis_mobile/build/web/. flutter_web/

# Полный деплой: сборка фронта + пересборка контейнера
flutter-deploy: flutter-build
    docker-compose build frontend
    docker-compose up -d frontend