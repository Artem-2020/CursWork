from typing import Protocol

from app.models import DetectionResult, MetricPoint


class AnomalyDetector(Protocol):
    """
    Any class that implements this interface can be used as a detector.

    Using Protocol (structural subtyping) means concrete detectors do not
    need to import or inherit from this file — they just need the right shape.
    """

    def detect(self, metric_name: str, points: list[MetricPoint]) -> DetectionResult:
        """
        Analyse `points` and decide whether the latest value is anomalous.

        Must always return a DetectionResult, never raise.
        """
        ...
