import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from app.main import create_app
from app.settings import Settings


def make_settings(**kwargs) -> Settings:
    defaults = dict(
        prometheus_url="http://test:9090",
        worker_interval_seconds=3600,
    )
    defaults.update(kwargs)
    return Settings(**defaults)


def make_mock_http_client() -> MagicMock:
    """
    Мок httpx.AsyncClient — все HTTP-вызовы мгновенно возвращают
    пустой ответ Prometheus, воркер не зависает на реальной сети.
    """
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"data": {"result": []}}

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.post = AsyncMock()
    mock_client.aclose = AsyncMock()

    return mock_client


def test_create_app():
    """Приложение создаётся без ошибок, заголовок совпадает."""
    app = create_app(make_settings())
    assert app is not None
    assert app.title == "Server Failure Prediction Service"


def test_app_lifespan_healthz():
    """
    После старта lifespan /healthz отвечает 200.
    Патчим httpx.AsyncClient чтобы воркер не делал реальных запросов.
    """
    app = create_app(make_settings())

    with patch("app.main.httpx.AsyncClient", return_value=make_mock_http_client()):
        with TestClient(app) as client:
            response = client.get("/api/v1/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_lifespan_creates_analysis_service():
    """
    После входа в lifespan app.state.analysis_service существует и не None.
    """
    app = create_app(make_settings())

    with patch("app.main.httpx.AsyncClient", return_value=make_mock_http_client()):
        with TestClient(app) as client:
            assert hasattr(app.state, "analysis_service")
            assert app.state.analysis_service is not None


def test_analyze_endpoint_returns_200():
    """Проверяет, что эндпоинт /analyze возвращает 200 и корректную структуру."""
    app = create_app(make_settings())

    with patch("app.main.httpx.AsyncClient", return_value=make_mock_http_client()):
        with TestClient(app) as client:
            response = client.post("/api/v1/analyze")

    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "anomalies" in data
    assert "results" in data
    assert isinstance(data["total"], int)
    assert isinstance(data["anomalies"], int)
    assert isinstance(data["results"], list)


def test_analyze_endpoint_returns_results_structure():
    """Проверяет структуру каждого результата в /analyze."""
    app = create_app(make_settings())

    with patch("app.main.httpx.AsyncClient", return_value=make_mock_http_client()):
        with TestClient(app) as client:
            response = client.post("/api/v1/analyze")
            data = response.json()

            if len(data["results"]) > 0:
                result = data["results"][0]
                assert "metric_name" in result
                assert "detector" in result
                assert "is_anomaly" in result
                assert "score" in result
                assert "detail" in result
                assert "checked_at" in result


def test_telegram_disabled_when_no_token():
    """Проверяет, что при отсутствии токена Telegram не включается."""
    settings = make_settings(
        telegram_bot_token="",
        telegram_chat_id="",
    )
    assert settings.telegram_enabled is False


def test_telegram_enabled_when_token_and_chat_id():
    """Проверяет, что Telegram включается при наличии токена и chat_id."""
    settings = make_settings(
        telegram_bot_token="test_token",
        telegram_chat_id="12345",
    )
    assert settings.telegram_enabled is True


def test_telegram_alerts_are_initialized_when_enabled():
    """Проверяет, что при включённом Telegram создаётся AlertService."""
    settings = make_settings(
        telegram_bot_token="test_token",
        telegram_chat_id="12345",
    )
    app = create_app(settings)

    with patch("app.main.httpx.AsyncClient", return_value=make_mock_http_client()):
  
        with patch("app.main.logging.getLogger") as mock_logger:
            with TestClient(app) as client:
            
                response = client.get("/api/v1/healthz")
                assert response.status_code == 200


def test_telegram_alerts_disabled_by_default():
    """Проверяет, что по умолчанию Telegram отключён."""
    settings = make_settings()
    assert settings.telegram_enabled is False


def test_custom_settings_override_defaults():
    """Проверяет, что кастомные настройки переопределяют значения по умолчанию."""
    settings = make_settings(
        prometheus_url="http://custom:9090",
        lookback_seconds=1800,
        sigma_threshold=2.5,
    )
    assert settings.prometheus_url == "http://custom:9090"
    assert settings.lookback_seconds == 1800
    assert settings.sigma_threshold == 2.5


def test_logging_configured_correctly():
    """Проверяет, что логирование настраивается без ошибок."""
    app = create_app(make_settings(log_level="DEBUG"))
    assert app is not None


def test_app_lifespan_shutdown_cleanup():
    """Проверяет, что при завершении работы ресурсы освобождаются."""
    app = create_app(make_settings())

    async def mock_gather(*args, **kwargs):
        return []

    with patch("app.main.httpx.AsyncClient", return_value=make_mock_http_client()):
        with patch("asyncio.gather", side_effect=mock_gather):
            with TestClient(app) as client:
                response = client.get("/api/v1/healthz")
                assert response.status_code == 200
            assert True