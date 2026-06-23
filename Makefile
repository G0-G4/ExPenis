.PHONY: up down build lock logs flutter-build flutter-deploy

up:
	docker-compose up -d

down:
	docker-compose down

build:
	docker-compose build

lock:
	uv pip compile pyproject.toml -o uv.lock

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