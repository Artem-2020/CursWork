import logging
from datetime import datetime, timedelta, timezone

from app.detector.analysis_service import AnalysisService
from app.models import DetectionResult
from app.notifications.formatter import format_alert
from app.notifications.notifier import NotifierProtocol

logger = logging.getLogger(__name__)


class AlertService:
    """
    Runs one analysis cycle and sends Telegram alerts for anomalies found.

    Depends on NotifierProtocol — not on TelegramNotifier directly.
    Any object with async send(text) -> bool can be injected,
    including test doubles, without modifying this class.

    Cooldown: once an alert fires for a (metric, detector) pair,
    it is suppressed until `cooldown_minutes` have elapsed.
    This prevents alert storms when a metric stays anomalous for many cycles.
    """

    def __init__(
        self,
        analysis: AnalysisService,
        notifier: NotifierProtocol,
        cooldown_minutes: int = 15,
    ) -> None:
        self._analysis = analysis
        self._notifier = notifier
        self._cooldown = timedelta(minutes=cooldown_minutes)
        # (metric_name, detector_value) → last alert sent at
        self._last_alerted: dict[tuple[str, str], datetime] = {}

    async def run(self) -> list[DetectionResult]:
        """
        Analyse all metrics, send alerts for anomalies not on cooldown.
        Always returns the full result list so the worker can log stats.
        """
        results: list[DetectionResult] = await self._analysis.run()

        for result in results:
            if result.is_anomaly:
                await self._maybe_alert(result)

        return results

    async def _maybe_alert(self, result: DetectionResult) -> None:
        """Send an alert only if the cooldown for this metric+detector has expired."""
        key = (result.metric_name, result.detector.value)
        now = datetime.now(tz=timezone.utc)
        last = self._last_alerted.get(key)

        if last is not None and (now - last) < self._cooldown:
            remaining = int((self._cooldown - (now - last)).total_seconds() / 60)
            logger.debug(
                "alert suppressed by cooldown: %s/%s — %d min remaining",
                result.metric_name,
                result.detector.value,
                remaining,
            )
            return

        message = format_alert(result)
        sent = await self._notifier.send(message)

        if sent:
            self._last_alerted[key] = now
            logger.info(
                "alert sent: metric=%s detector=%s score=%.4f",
                result.metric_name,
                result.detector.value,
                result.score,
            )
        else:
            logger.warning(
                "alert failed to send: metric=%s detector=%s",
                result.metric_name,
                result.detector.value,
            )
