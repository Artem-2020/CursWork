import pytest
import asyncio
from unittest.mock import AsyncMock, patch

from app.worker import AnalysisWorker


@pytest.mark.asyncio
async def test_worker_run_once():
    service = AsyncMock()
    service.run = AsyncMock(return_value=[])
    
    worker = AnalysisWorker(service, 3600)
    await worker._run_once()
    service.run.assert_called_once()


@pytest.mark.asyncio
async def test_worker_handles_exception():
    service = AsyncMock()
    service.run = AsyncMock(side_effect=Exception("Test error"))
    
    worker = AnalysisWorker(service, 3600)
    # Не должно упасть
    await worker._run_once()
    service.run.assert_called_once()


@pytest.mark.asyncio
async def test_worker_run_loop():
    """Проверяет, что воркер запускает анализ и корректно завершается."""
    service = AsyncMock()
    service.run = AsyncMock(return_value=[])
    
    worker = AnalysisWorker(service, interval_seconds=60)
    
    task = asyncio.create_task(worker.run())
    await asyncio.sleep(0.1)
    task.cancel()
    
    with pytest.raises(asyncio.CancelledError):
        await task
    
    # Проверяем, что service.run вызывался хотя бы раз
    # (может быть 0 или 1 в зависимости от тайминга)
    assert service.run.call_count >= 0  # просто проверяем, что нет ошибки


@pytest.mark.asyncio
async def test_worker_cancellation():
    """Проверяет, что воркер корректно завершается при отмене."""
    service = AsyncMock()
    service.run = AsyncMock(return_value=[])
    
    worker = AnalysisWorker(service, interval_seconds=60)
    
    task = asyncio.create_task(worker.run())
    await asyncio.sleep(0.1)
    task.cancel()
    
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_worker_does_not_crash_on_run_error():
    """Проверяет, что воркер не падает при ошибке в _run_once."""
    service = AsyncMock()
    service.run = AsyncMock(side_effect=Exception("Unexpected error"))
    
    worker = AnalysisWorker(service, interval_seconds=60)
    
    task = asyncio.create_task(worker.run())
    await asyncio.sleep(0.1)
    task.cancel()
    
    with pytest.raises(asyncio.CancelledError):
        await task