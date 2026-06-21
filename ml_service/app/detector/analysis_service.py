import logging

from app.detector.base import AnomalyDetector
from app.models import DetectionResult
from app.prometheus.client import PrometheusClient

logger = logging.getLogger(__name__)


class AnalysisService:
    """
    Orchestrates one full analysis cycle:
      1. Fetch time-series data from Prometheus for every metric
      2. Run each registered detector on each metric
      3. Return all results

    This class has no ML logic — it delegates to detectors and the
    Prometheus client, keeping each piece independently testable.
    """

    def __init__(
        self,
        prometheus: PrometheusClient,
        detectors: list[AnomalyDetector],
        metrics: list[str],
        lookback_seconds: int,
    ) -> None:
        self._prometheus = prometheus
        self._detectors = detectors
        self._metrics = metrics
        self._lookback = lookback_seconds

    async def run(self) -> list[DetectionResult]:
        """
        Analyse all metrics with all detectors.
        Errors in individual metrics are logged and skipped so a single
        unavailable metric never blocks the whole cycle.
        """
        results: list[DetectionResult] = []

        for metric_name in self._metrics:
            points = await self._prometheus.fetch_range(metric_name, self._lookback)

            if not points:
                logger.warning("no data for metric '%s', skipping", metric_name)
                continue

            for detector in self._detectors:
                result = detector.detect(metric_name, points)
                results.append(result)

                if result.is_anomaly:
                    logger.warning(
                        "ANOMALY detected | metric=%s detector=%s score=%.4f | %s",
                        result.metric_name,
                        result.detector,
                        result.score,
                        result.detail,
                    )

        return results
