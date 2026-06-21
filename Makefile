.PHONY: help deps test test-agent test-ml coverage lint lint-agent lint-ml \
        build run docker-up docker-down clean


AGENT_DIR := agent
ML_DIR := ml_service
DOCKER_COMPOSE := docker-compose

help:
	@echo "Доступные команды:"
	@echo "  deps           Установить зависимости для Go и Python"
	@echo "  test           Запустить все тесты (агент + ML)"
	@echo "  test-agent     Запустить тесты Go-агента"
	@echo "  test-ml        Запустить тесты ML-сервиса"
	@echo "  coverage       Показать покрытие тестов (агент и ML)"
	@echo "  lint           Запустить SAST-анализ (gosec + bandit)"
	@echo "  lint-agent     Запустить gosec для Go-агента"
	@echo "  lint-ml        Запустить bandit для ML-сервиса"
	@echo "  build          Собрать бинарные файлы (без Docker)"
	@echo "  run            Запустить через docker-compose up"
	@echo "  docker-up      Запустить все сервисы в фоне"
	@echo "  docker-down    Остановить и удалить контейнеры"
	@echo "  clean          Очистить временные файлы и кеш"


deps:
	cd $(AGENT_DIR) && go mod download
	cd $(ML_DIR) && pip install -r requirements.txt

test: test-agent test-ml

test-agent:
	cd $(AGENT_DIR) && go test ./... -cover

test-ml:
	cd $(ML_DIR) && pytest tests/ -v

coverage:
	@echo "=== Go-агент ==="
	cd $(AGENT_DIR) && go test ./... -coverprofile=coverage.out && go tool cover -func=coverage.out | tail -1
	@echo "\n=== ML-сервис ==="
	cd $(ML_DIR) && pytest tests/ --cov=app --cov-report=term

lint: lint-agent lint-ml

lint-agent:
	@which gosec > /dev/null || (echo "Установите gosec: go install github.com/securego/gosec/v2/cmd/gosec@latest" && exit 1)
	cd $(AGENT_DIR) && gosec ./...

lint-ml:
	@which bandit > /dev/null || (echo "Установите bandit: pip install bandit" && exit 1)
	cd $(ML_DIR) && bandit -r app/ -ll

build: build-agent build-ml

build-agent:
	cd $(AGENT_DIR) && go build -o bin/agent ./cmd/agent

build-ml:


docker-up:
	$(DOCKER_COMPOSE) up --build -d

docker-down:
	$(DOCKER_COMPOSE) down

run:
	$(DOCKER_COMPOSE) up --build

clean:
	cd $(AGENT_DIR) && rm -rf bin/ coverage.out
	cd $(ML_DIR) && rm -rf .pytest_cache/ __pycache__/ .coverage
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete