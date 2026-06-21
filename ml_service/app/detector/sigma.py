import logging
from datetime import datetime, timezone

import numpy as np

from app.models import DetectionResult, DetectorKind, MetricPoint

logger = logging.getLogger(__name__)


class SigmaDetector:
    """
    Detects anomalies using the 3-sigma (z-score) rule.

    A point is anomalous when it deviates more than `threshold` standard
    deviations from the rolling mean of the provided window.

    Strengths:
        - Explainable: "the value was X std deviations above the mean"
        - No training phase required
        - Fast on small windows

    Limitations:
        - Univariate: analyses each metric independently
        - Sensitive to non-stationary baselines (e.g. daily CPU cycles)
    """

    def __init__(self, threshold: float = 3.0, min_points: int = 10) -> None:
        if threshold <= 0:
            raise ValueError("threshold must be positive")
        self._threshold = threshold
        self._min_points = min_points

    def detect(self, metric_name: str, points: list[MetricPoint]) -> DetectionResult:
        """
        Compute z-score of the latest point against the whole window.
        Returns is_anomaly=False when there are not enough points.
        """
        if len(points) < self._min_points:
            return self._insufficient_data(metric_name, len(points))

        values = np.array([p.value for p in points], dtype=np.float64)
        mean = values.mean()
        std = values.std()

        latest = values[-1]

        # Avoid division by zero when all values are identical.
        if std < 1e-9:
            return DetectionResult(
                metric_name=metric_name,
                detector=DetectorKind.SIGMA,
                is_anomaly=False,
                score=0.0,
                detail="standard deviation is zero — all values identical",
            )

        z_score = abs((latest - mean) / std)
        is_anomaly = z_score > self._threshold

        logger.debug(
            "sigma | %s | latest=%.2f mean=%.2f std=%.2f z=%.2f anomaly=%s",
            metric_name, latest, mean, std, z_score, is_anomaly,
        )

        return DetectionResult(
            metric_name=metric_name,
            detector=DetectorKind.SIGMA,
            is_anomaly=is_anomaly,
            score=round(z_score, 4),
            detail=f"z={z_score:.2f}, threshold={self._threshold}, mean={mean:.2f}, std={std:.2f}",
        )

    def _insufficient_data(self, metric_name: str, count: int) -> DetectionResult:
        return DetectionResult(
            metric_name=metric_name,
            detector=DetectorKind.SIGMA,
            is_anomaly=False,
            score=0.0,
            checked_at=datetime.now(tz=timezone.utc),
            detail=f"not enough data: {count} points, need {self._min_points}",
        )
