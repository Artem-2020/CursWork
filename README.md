# Курсовая работа

## Система мониторинга и прогнозирования сбоев серверов

**Выполнил:** Орехов Артем Алексеевич  
**Группа:** 221331  
**Вариант:** 20

---

## Кратко о проекте

Проект представляет собой распределенную систему наблюдения за состоянием сервера. Она собирает показатели загрузки CPU, оперативной памяти и диска, сохраняет их в Prometheus, отображает в Grafana и передает в ML-сервис для поиска аномалий.

Основная идея системы: не просто показать текущую нагрузку, а заранее заметить нетипичное поведение сервера и отправить предупреждение через Telegram.

Система состоит из четырех основных частей:

| Компонент | Назначение |
|---|---|
| Go-агент | Сбор системных метрик и публикация `/metrics` |
| Prometheus | Хранение временных рядов и выдача данных по API |
| ML-сервис | Анализ метрик, поиск аномалий, REST API |
| Grafana | Визуализация состояния сервера |
| Telegram | Канал уведомлений об аномалиях |

---

## Используемые технологии

| Задача | Технологии |
|---|---|
| Сбор метрик | Go 1.22, gopsutil, Prometheus client |
| HTTP API агента | Go `net/http` |
| Хранение метрик | Prometheus 2.52 |
| Анализ данных | Python 3.11, NumPy, scikit-learn |
| API ML-сервиса | FastAPI, uvicorn, pydantic |
| Визуализация | Grafana 10.4 |
| Уведомления | Telegram Bot API |
| Контейнеризация | Docker, Docker Compose |
| Тестирование | Go test, pytest |
| SAST | gosec, bandit |

---

## Как работает система

```text
        каждые 15 секунд
┌────────────────────┐      /metrics       ┌────────────────────┐
│ Go-агент            │ ─────────────────▶ │ Prometheus          │
│ порт 9100           │                    │ порт 9090           │
│ CPU / RAM / Disk    │                    │ time-series storage │
└────────────────────┘                    └─────────┬──────────┘
                                                     │
                                                     │ query_range API
                                                     ▼
                                           ┌────────────────────┐
                                           │ ML-сервис           │
                                           │ порт 8000           │
                                           │ Sigma + IF          │
                                           └─────────┬──────────┘
                                                     │
                                                     │ Bot API
                                                     ▼
                                           ┌────────────────────┐
                                           │ Telegram            │
                                           │ уведомления         │
                                           └────────────────────┘

┌────────────────────┐
│ Grafana             │ ◀──── datasource: Prometheus
│ порт 3000           │
│ дашборд мониторинга │
└────────────────────┘
```

Последовательность работы:

1. Go-агент запускается на порту `9100`.
2. Каждые `15s` агент получает системные показатели через `gopsutil`.
3. Метрики публикуются в формате Prometheus на эндпоинте `/metrics`.
4. Prometheus регулярно опрашивает агент и сохраняет значения.
5. ML-сервис каждые `60s` запрашивает окно последних данных из Prometheus.
6. Каждая метрика проверяется двумя алгоритмами: `SigmaDetector` и `IsolationForestDetector`.
7. Если обнаружена аномалия, `AlertService` проверяет cooldown и отправляет сообщение в Telegram.
8. Grafana показывает текущее состояние и историю загрузки сервера.

---

## Структура проекта

```text
server-failure-prediction/
├── agent/                         # Go-агент сбора метрик
│   ├── cmd/agent/
│   │   ├── main.go                # точка входа приложения
│   │   ├── config.go              # чтение настроек из env
│   │   └── *_test.go              # тесты запуска и конфигурации
│   ├── internal/
│   │   ├── collector/
│   │   │   ├── collector.go       # интерфейс сборщика
│   │   │   ├── system_collector.go# получение CPU/RAM/Disk
│   │   │   ├── gauges.go          # регистрация Prometheus Gauge
│   │   │   ├── scraper.go         # периодический сбор
│   │   │   └── *_test.go
│   │   └── server/
│   │       ├── server.go          # HTTP /metrics и /healthz
│   │       └── server_test.go
│   ├── Dockerfile
│   ├── go.mod
│   └── go.sum
│
├── ml_service/                    # Python-сервис анализа
│   ├── app/
│   │   ├── main.py                # создание FastAPI-приложения
│   │   ├── settings.py            # настройки сервиса
│   │   ├── models.py              # модели данных
│   │   ├── alert_service.py       # cooldown и отправка алертов
│   │   ├── api/router.py          # REST API
│   │   ├── detector/              # алгоритмы анализа
│   │   ├── prometheus/client.py   # клиент Prometheus API
│   │   ├── notifications/         # Telegram-уведомления
│   │   └── worker/worker.py       # фоновый цикл анализа
│   ├── tests/                     # тесты Python-кода
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py                    # запуск uvicorn
│
├── infra/
│   ├── prometheus.yml             # настройка scrape для агента
│   └── grafana/
│       ├── provisioning/          # автоподключение datasource/dashboard
│       └── dashboards/
│           └── server-agent.json  # готовый дашборд Grafana
│
├── docker-compose.yml             # запуск всей системы
├── Makefile                       # команды разработки
├── .env.example                   # пример переменных окружения
└── README.md
```

---

## Объяснение рабочего кода

### Go-агент

Go-агент отвечает за получение системных метрик и передачу их Prometheus.

Главные файлы:

| Файл | Роль |
|---|---|
| `agent/cmd/agent/main.go` | собирает зависимости, создает collector, scraper и HTTP-сервер |
| `agent/cmd/agent/config.go` | читает `LISTEN_ADDR`, `SCRAPE_INTERVAL`, `DISK_PATH`, `LOG_LEVEL` |
| `agent/internal/collector/system_collector.go` | получает CPU, RAM и диск через `gopsutil` |
| `agent/internal/collector/gauges.go` | описывает Prometheus-метрики |
| `agent/internal/collector/scraper.go` | запускает периодический сбор по таймеру |
| `agent/internal/server/server.go` | поднимает HTTP-сервер с `/metrics` и `/healthz` |

Агент экспортирует три основные метрики:

| Метрика | Значение |
|---|---|
| `server_agent_cpu_usage_percent` | загрузка CPU в процентах |
| `server_agent_memory_usage_percent` | использование RAM в процентах |
| `server_agent_disk_usage_percent` | использование диска в процентах |

### ML-сервис

ML-сервис получает данные из Prometheus и проверяет их на аномалии.

Главные файлы:

| Файл | Роль |
|---|---|
| `ml_service/app/main.py` | создает FastAPI, PrometheusClient, детекторы, воркер и notifier |
| `ml_service/app/settings.py` | хранит настройки анализа и уведомлений |
| `ml_service/app/prometheus/client.py` | делает запросы к Prometheus `query_range` |
| `ml_service/app/detector/sigma.py` | статистический детектор по правилу трех сигм |
| `ml_service/app/detector/isolation_forest.py` | ML-детектор на Isolation Forest |
| `ml_service/app/detector/analysis_service.py` | запускает детекторы для всех метрик |
| `ml_service/app/alert_service.py` | отсекает повторные уведомления через cooldown |
| `ml_service/app/notifications/notifier.py` | отправляет сообщения в Telegram |
| `ml_service/app/api/router.py` | предоставляет `/healthz` и `/analyze` |
| `ml_service/app/worker/worker.py` | автоматически запускает анализ по расписанию |

### Prometheus

Prometheus настроен в `infra/prometheus.yml`. Он опрашивает Go-агент по адресу `agent:9100` и сохраняет метрики как временные ряды. Эти данные затем используются и Grafana, и ML-сервисом.

### Grafana

Grafana автоматически получает datasource и dashboard из папки `infra/grafana/provisioning`. Вручную импортировать JSON не нужно. После запуска Docker Compose дашборд появляется в интерфейсе Grafana.

---

## Алгоритмы обнаружения аномалий

### SigmaDetector

Детектор использует правило трех сигм. Он сравнивает последнее значение метрики со средним значением за выбранное окно.

```text
z = |last_value - mean| / std
anomaly = z > threshold
```

По умолчанию порог равен `3.0`. Такой подход простой, быстрый и хорошо объяснимый: если значение сильно выбивается из обычного диапазона, оно считается подозрительным.

### IsolationForestDetector

Isolation Forest ищет точки, которые отличаются от большинства наблюдений. Для анализа используются признаки:

```text
value
rolling_mean_5
rolling_std_5
```

Это позволяет учитывать не только само значение метрики, но и короткий локальный контекст. Детектор особенно полезен для поиска нелинейных или неочевидных выбросов.

---

## Быстрый запуск через Docker

### 1. Подготовить `.env`

Скопируйте пример переменных окружения:

```bash
cp .env.example .env
```

Для Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Откройте `.env` и укажите значения:

```env
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=change_me

TELEGRAM_BOT_TOKEN=change_me
TELEGRAM_CHAT_ID=change_me
```

Если Telegram-токен и chat id не указаны, система продолжит работать, но уведомления отправляться не будут.

### 2. Запустить контейнеры

```bash
docker-compose up --build
```

Или через Makefile:

```bash
make run
```

Для запуска в фоне:

```bash
make docker-up
```

### 3. Открыть сервисы

| Сервис | Адрес |
|---|---|
| Go-агент, метрики | http://localhost:9100/metrics |
| Go-агент, healthcheck | http://localhost:9100/healthz |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |
| ML-сервис, healthcheck | http://localhost:8000/api/v1/healthz |
| Swagger ML-сервиса | http://localhost:8000/docs |

Данные для входа в Grafana берутся из `.env`. По умолчанию логин `admin`, пароль `change_me`.

---

## Локальный запуск без Docker

### Go-агент

```bash
cd agent
go mod download
go run ./cmd/agent
```

Пример запуска с переопределением параметров:

```bash
LISTEN_ADDR=:9100 SCRAPE_INTERVAL=15s DISK_PATH=/ LOG_LEVEL=debug go run ./cmd/agent
```

На Windows PowerShell переменные можно задать так:

```powershell
$env:LISTEN_ADDR=":9100"
$env:SCRAPE_INTERVAL="15s"
$env:DISK_PATH="/"
$env:LOG_LEVEL="debug"
go run ./cmd/agent
```

### ML-сервис

```bash
cd ml_service
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

Для Windows PowerShell:

```powershell
cd ml_service
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Для полноценной работы ML-сервису нужен доступный Prometheus. Поэтому удобнее запускать весь стек через Docker Compose.

---

## REST API ML-сервиса

| Метод | Эндпоинт | Назначение |
|---|---|---|
| `GET` | `/api/v1/healthz` | Проверка, что сервис запущен |
| `POST` | `/api/v1/analyze` | Ручной запуск анализа метрик |

Пример ручного запуска анализа:

```bash
curl -X POST http://localhost:8000/api/v1/analyze
```

Пример ответа:

```json
{
  "total": 6,
  "anomalies": 1,
  "results": [
    {
      "metric_name": "server_agent_cpu_usage_percent",
      "detector": "sigma",
      "is_anomaly": true,
      "score": 4.0982,
      "checked_at": "2026-06-07T17:54:44Z",
      "detail": "z=4.10, threshold=3.0, mean=15.39, std=2.40"
    }
  ]
}
```

---

## Конфигурация

### Go-агент

| Переменная | Значение по умолчанию | Описание |
|---|---|---|
| `LISTEN_ADDR` | `:9100` | Адрес HTTP-сервера |
| `SCRAPE_INTERVAL` | `15s` | Интервал сбора системных метрик |
| `DISK_PATH` | `/` | Путь диска для мониторинга |
| `LOG_LEVEL` | `info` | Уровень логирования |

### ML-сервис

| Переменная | Значение по умолчанию | Описание |
|---|---|---|
| `PROMETHEUS_URL` | `http://prometheus:9090` | Адрес Prometheus |
| `LOOKBACK_SECONDS` | `3600` | Размер окна анализа в секундах |
| `WORKER_INTERVAL_SECONDS` | `60` | Интервал фонового анализа |
| `MIN_DATA_POINTS` | `10` | Минимум точек для анализа |
| `SIGMA_THRESHOLD` | `3.0` | Порог z-score для SigmaDetector |
| `IFOREST_CONTAMINATION` | `0.05` | Ожидаемая доля аномалий |
| `ALERT_COOLDOWN_MINUTES` | `15` | Пауза между повторными алертами |
| `TELEGRAM_BOT_TOKEN` | пусто | Токен Telegram-бота |
| `TELEGRAM_CHAT_ID` | пусто | ID чата или канала |
| `LOG_LEVEL` | `INFO` | Уровень логирования |

---

## Тестирование

Запуск всех тестов:

```bash
make test
```

Только Go-агент:

```bash
make test-agent
```

Только ML-сервис:

```bash
make test-ml
```

Покрытие:

```bash
make coverage
```

Проверки безопасности:

```bash
make lint
```

Для SAST нужны установленные `gosec` и `bandit`. Если их нет, Makefile выведет команду установки.

---

## Основные Make-команды

```bash
make help          # список команд
make deps          # загрузить зависимости Go и Python
make test          # запустить все тесты
make test-agent    # тесты Go-агента
make test-ml       # тесты ML-сервиса
make coverage      # отчет по покрытию
make lint          # gosec + bandit
make build         # сборка Go-агента
make run           # docker-compose up --build
make docker-up     # запуск контейнеров в фоне
make docker-down   # остановка контейнеров
make clean         # очистка временных файлов
```

---

## Grafana Dashboard

Дашборд находится в файле:

```text
infra/grafana/dashboards/server-agent.json
```

Он подключается автоматически через provisioning и показывает:

| Блок | Что отображает |
|---|---|
| CPU Load | текущую загрузку процессора |
| Memory Pressure | текущее использование RAM |
| Disk Occupancy | заполнение диска |
| Resource Usage Timeline | общий график CPU/RAM/Disk |
| Current Saturation | текущие значения в виде bar-gauge |
| Average CPU In Window | среднюю загрузку CPU |
| Peak Values | максимальные значения за выбранное окно |

Пороговые зоны:

| Диапазон | Интерпретация |
|---|---|
| до 70% | нормальное состояние |
| 70-90% | повышенная нагрузка |
| выше 90% | критическая нагрузка |

---

## Что было реализовано

В рамках курсовой работы реализованы:

1. Go-агент для сбора CPU, RAM и disk usage.
2. Экспорт метрик в формате Prometheus.
3. Prometheus-конфигурация для регулярного сбора метрик.
4. FastAPI ML-сервис с ручным и фоновым запуском анализа.
5. Два независимых алгоритма обнаружения аномалий.
6. Telegram-уведомления с защитой от повторной отправки.
7. Grafana-дашборд для визуального контроля состояния сервера.
8. Docker Compose для запуска всей инфраструктуры одной командой.
9. Набор unit-тестов для Go и Python частей.
10. Makefile для удобного запуска типовых команд.

---

## Итог

Проект демонстрирует полный цикл мониторинга серверной инфраструктуры: от сбора низкоуровневых системных метрик до анализа, визуализации и автоматического оповещения. Архитектура разделена на независимые компоненты, поэтому систему можно расширять: добавлять новые метрики, подключать дополнительные детекторы, менять канал уведомлений или дорабатывать Grafana-дашборды без переписывания всего проекта.
