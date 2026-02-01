.PHONY: up down build lock

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
