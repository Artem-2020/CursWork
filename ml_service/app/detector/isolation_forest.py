import logging
from datetime import datetime, timezone

import numpy as np
from sklearn.ensemble import IsolationForest

from app.models import DetectionResult, DetectorKind, MetricPoint

logger = logging.getLogger(__name__)


class IsolationForestDetector:
    """
    Detects anomalies using scikit-learn's Isolation Forest.

    Unlike SigmaDetector, this model works on multivariate windows:
    each sample is a tuple of (value, rolling_mean, rolling_std), which
    lets the model learn *patterns* rather than just absolute thresholds.

    Strengths:
        - Catches complex, non-linear anomalies
        - Unsupervised: no labelled anomaly data required
        - Works across multiple metrics simultaneously

    Limitations:
        - Needs more data to be reliable (>= 50 points recommended)
        - Less explainable than sigma: score is a relative isolation depth
        - Retrains on every call (acceptable for this scale)
    """

    def __init__(self, contamination: float = 0.05, min_points: int = 20) -> None:
        if not (0.0 < contamination < 0.5):
            raise ValueError("contamination must be in (0, 0.5)")
        self._contamination = contamination
        self._min_points = min_points

    def detect(self, metric_name: str, points: list[MetricPoint]) -> DetectionResult:
        """
        Build a feature matrix from `points`, fit Isolation Forest,
        and classify the last point as normal or anomalous.
        """
        if len(points) < self._min_points:
            return self._insufficient_data(metric_name, len(points))

        features = self._build_features(points)

        model = IsolationForest(
            contamination=self._contamination,
            random_state=42,
            n_jobs=1,
        )
        model.fit(features)

        # predict returns +1 (normal) or -1 (anomaly).
        prediction = model.predict(features[-1].reshape(1, -1))[0]
        # score_samples returns negative anomaly score; higher = more normal.
        raw_score = float(model.score_samples(features[-1].reshape(1, -1))[0])

        is_anomaly = prediction == -1

        logger.debug(
            "iforest | %s | score=%.4f anomaly=%s",
            metric_name, raw_score, is_anomaly,
        )

        return DetectionResult(
            metric_name=metric_name,
            detector=DetectorKind.ISOLATION_FOREST,
            is_anomaly=is_anomaly,
            score=round(raw_score, 4),
            detail=f"if_score={raw_score:.4f}, contamination={self._contamination}",
        )

    @staticmethod
    def _build_features(points: list[MetricPoint]) -> np.ndarray:
        """
        Construct a (N, 3) feature matrix:
            col 0 — raw value
            col 1 — rolling mean over last 5 points
            col 2 — rolling std  over last 5 points

        Rolling statistics give the model temporal context so it can
        distinguish a high-but-stable value from a sudden spike.
        """
        values = np.array([p.value for p in points], dtype=np.float64)
        n = len(values)
        window = 5

        means = np.array([
            values[max(0, i - window + 1): i + 1].mean()
            for i in range(n)
        ])
        stds = np.array([
            values[max(0, i - window + 1): i + 1].std()
            for i in range(n)
        ])

        return np.column_stack([values, means, stds])

    def _insufficient_data(self, metric_name: str, count: int) -> DetectionResult:
        return DetectionResult(
            metric_name=metric_name,
            detector=DetectorKind.ISOLATION_FOREST,
            is_anomaly=False,
            score=0.0,
            checked_at=datetime.now(tz=timezone.utc),
            detail=f"not enough data: {count} points, need {self._min_points}",
        )
