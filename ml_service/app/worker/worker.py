import asyncio
import logging
from typing import Protocol

from app.models import DetectionResult

logger = logging.getLogger(__name__)


class Runnable(Protocol):
    """
    Any object with async run() -> list[DetectionResult] satisfies this Protocol.
    Decouples AnalysisWorker from both AnalysisService and AlertService —
    Open/Closed Principle: add new runnables without modifying the worker.
    """

    async def run(self) -> list[DetectionResult]:
        ...


class AnalysisWorker:
    """
    Runs any Runnable on a fixed interval in the background.

    Stops cleanly when the asyncio Task is cancelled:
    CancelledError propagates out of asyncio.sleep(), is logged, then
    re-raised so asyncio.gather() sees the task finished normally.
    """

    def __init__(self, service: Runnable, interval_seconds: int) -> None:
        self._service = service
        self._interval = interval_seconds

    async def run(self) -> None:
        logger.info("analysis worker started (interval=%ds)", self._interval)

        try:
            while True:
                await self._run_once()
                await asyncio.sleep(self._interval)
        except asyncio.CancelledError:
            logger.info("analysis worker stopped")
            raise

    async def _run_once(self) -> None:
        try:
            results = await self._service.run()
            anomalies = [r for r in results if r.is_anomaly]
            logger.info(
                "analysis cycle complete: %d results, %d anomalies",
                len(results),
                len(anomalies),
            )
        except Exception as exc:
            logger.error("analysis cycle failed: %s", exc, exc_info=True)
