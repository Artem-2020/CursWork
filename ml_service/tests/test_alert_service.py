import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta, timezone

from app.alert_service import AlertService
from app.models import DetectionResult, DetectorKind


@pytest.mark.asyncio
async def test_alert_service_sends_alert_on_anomaly():
    """Проверяет, что при аномалии отправляется уведомление."""
    mock_analysis = AsyncMock()
    mock_notifier = AsyncMock()
    mock_notifier.send = AsyncMock(return_value=True)

    result = DetectionResult(
        metric_name="cpu",
        detector=DetectorKind.SIGMA,
        is_anomaly=True,
        score=4.5,
        detail="test",
    )
    mock_analysis.run = AsyncMock(return_value=[result])

    service = AlertService(mock_analysis, mock_notifier, cooldown_minutes=15)
    results = await service.run()

    assert len(results) == 1
    assert results[0].is_anomaly is True
    mock_notifier.send.assert_called_once()


@pytest.mark.asyncio
async def test_alert_service_suppresses_duplicate_alerts():
    """Проверяет, что повторные алерты подавляются cooldown."""
    mock_analysis = AsyncMock()
    mock_notifier = AsyncMock()
    mock_notifier.send = AsyncMock(return_value=True)

    result = DetectionResult(
        metric_name="cpu",
        detector=DetectorKind.SIGMA,
        is_anomaly=True,
        score=4.5,
        detail="test",
    )
    mock_analysis.run = AsyncMock(return_value=[result])

    service = AlertService(mock_analysis, mock_notifier, cooldown_minutes=15)

    # Первый вызов — алерт должен отправиться
    await service.run()
    # Второй вызов — должен подавиться
    await service.run()

    # Должен быть только один вызов send
    assert mock_notifier.send.call_count == 1


@pytest.mark.asyncio
async def test_alert_service_no_alert_on_normal():
    """Проверяет, что при нормальном состоянии уведомления не отправляются."""
    mock_analysis = AsyncMock()
    mock_notifier = AsyncMock()

    result = DetectionResult(
        metric_name="cpu",
        detector=DetectorKind.SIGMA,
        is_anomaly=False,
        score=1.0,
        detail="normal",
    )
    mock_analysis.run = AsyncMock(return_value=[result])

    service = AlertService(mock_analysis, mock_notifier)
    await service.run()

    mock_notifier.send.assert_not_called()


@pytest.mark.asyncio
async def test_alert_service_sends_for_different_metrics():
    """Проверяет, что для разных метрик алерты отправляются независимо."""
    mock_analysis = AsyncMock()
    mock_notifier = AsyncMock()
    mock_notifier.send = AsyncMock(return_value=True)

    result1 = DetectionResult(
        metric_name="cpu",
        detector=DetectorKind.SIGMA,
        is_anomaly=True,
        score=4.5,
        detail="test",
    )
    result2 = DetectionResult(
        metric_name="memory",
        detector=DetectorKind.SIGMA,
        is_anomaly=True,
        score=4.2,
        detail="test",
    )
    mock_analysis.run = AsyncMock(return_value=[result1, result2])

    service = AlertService(mock_analysis, mock_notifier, cooldown_minutes=15)
    await service.run()

    # Должно быть 2 вызова send
    assert mock_notifier.send.call_count == 2


@pytest.mark.asyncio
async def test_alert_service_notifier_failure_does_not_crash():
    """Проверяет, что при ошибке notifier'а сервис не падает."""
    mock_analysis = AsyncMock()
    mock_notifier = AsyncMock()
    mock_notifier.send = AsyncMock(return_value=False)

    result = DetectionResult(
        metric_name="cpu",
        detector=DetectorKind.SIGMA,
        is_anomaly=True,
        score=4.5,
        detail="test",
    )
    mock_analysis.run = AsyncMock(return_value=[result])

    service = AlertService(mock_analysis, mock_notifier, cooldown_minutes=15)
    results = await service.run()

    assert len(results) == 1
    mock_notifier.send.assert_called_once()

@pytest.mark.asyncio
async def test_alert_service_cooldown_expires():
    """Проверяет, что после истечения cooldown алерт отправляется снова."""
    mock_analysis = AsyncMock()
    mock_notifier = AsyncMock()
    mock_notifier.send = AsyncMock(return_value=True)

    result = DetectionResult(
        metric_name="cpu",
        detector=DetectorKind.SIGMA,
        is_anomaly=True,
        score=4.5,
        detail="test",
    )
    mock_analysis.run = AsyncMock(return_value=[result])

    service = AlertService(mock_analysis, mock_notifier, cooldown_minutes=1)

    # Первый вызов — алерт отправляется
    await service.run()
    assert mock_notifier.send.call_count == 1

    # Имитируем, что прошло больше 1 минуты
    with patch("app.alert_service.datetime") as mock_datetime:
        # Устанавливаем время в будущем
        future_time = datetime.now(timezone.utc) + timedelta(minutes=2)
        mock_datetime.now.return_value = future_time
        mock_datetime.side_effect = lambda *args, **kw: datetime.now(*args, **kw)
        
        # Второй вызов — должен отправиться снова
        await service.run()
        assert mock_notifier.send.call_count == 2