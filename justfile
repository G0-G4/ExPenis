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
# что запустит GitHub Actions workflow сборки релиза с APK.
release-tag:
    @version=$(grep '^version:' frontend/pubspec.yaml | awk '{print $$2}' | cut -d '+' -f1); \
    echo "Creating tag v$$version"; \
    git tag "v$$version" && git push origin "v$$version"