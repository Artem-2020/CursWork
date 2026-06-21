import pytest
import httpx
from unittest.mock import AsyncMock
from datetime import datetime, timezone

from app.notifications.notifier import TelegramNotifier, TelegramConfig
from app.notifications.formatter import format_alert
from app.models import DetectionResult, DetectorKind


@pytest.mark.asyncio
async def test_telegram_notifier_send_success():
    config = TelegramConfig(bot_token="test_token", chat_id="12345")
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.raise_for_status = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    notifier = TelegramNotifier(config, mock_client)
    result = await notifier.send("Test message")

    assert result is True
    mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_telegram_notifier_send_http_error():
    """Проверяет, что при HTTP ошибке возвращается False."""
    config = TelegramConfig(bot_token="test_token", chat_id="12345")
    mock_client = AsyncMock()
    # Используем конкретное исключение, а не абстрактный класс
    mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))

    notifier = TelegramNotifier(config, mock_client)
    result = await notifier.send("Test message")

    assert result is False


def test_format_alert_default_time():
    result = DetectionResult(
        metric_name="server_agent_cpu_usage_percent",
        detector=DetectorKind.SIGMA,
        is_anomaly=True,
        score=4.1234,
        detail="z=4.12, threshold=3.0",
    )
    message = format_alert(result)

    assert "🔥 <b>ANOMALY DETECTED</b>" in message
    assert "server_agent_cpu_usage_percent" in message
    assert "sigma" in message
    assert "4.1234" in message


def test_format_alert_with_custom_time():
    result = DetectionResult(
        metric_name="server_agent_memory_usage_percent",
        detector=DetectorKind.ISOLATION_FOREST,
        is_anomaly=True,
        score=-0.7250,
        detail="if_score=-0.7250, contamination=0.05",
    )
    now = datetime(2026, 6, 7, 18, 0, 0, tzinfo=timezone.utc)
    message = format_alert(result, now)

    assert "🧠 <b>ANOMALY DETECTED</b>" in message
    assert "server_agent_memory_usage_percent" in message
    assert "isolation_forest" in message
    assert "-0.7250" in message
    assert "2026-06-07 18:00:00 UTC" in message


def test_format_alert_unknown_metric_uses_default_emoji():
    result = DetectionResult(
        metric_name="unknown_metric",
        detector=DetectorKind.SIGMA,
        is_anomaly=True,
        score=3.5,
        detail="test",
    )
    message = format_alert(result)

    assert "⚠️ <b>ANOMALY DETECTED</b>" in message