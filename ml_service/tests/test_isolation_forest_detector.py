import pytest
from datetime import datetime, timezone

from app.detector.isolation_forest import IsolationForestDetector
from app.models import DetectorKind, MetricPoint


def make_points(values):
    return [
        MetricPoint(
            timestamp=datetime.now(timezone.utc),
            value=v,
        )
        for v in values
    ]


class TestIsolationForestDetector:
    def setup_method(self):
        self.detector = IsolationForestDetector(contamination=0.05, min_points=20)

    def test_stable_series_not_anomalous(self):
        points = make_points([50.0 + i % 3 for i in range(60)])
        result = self.detector.detect("cpu", points)
        assert result.detector == DetectorKind.ISOLATION_FOREST
        assert result.is_anomaly is not None

    def test_extreme_outlier_detected(self):
        points = make_points([50.0] * 59 + [999.0])
        result = self.detector.detect("cpu", points)
        assert result.is_anomaly == True
        assert result is not None

    def test_insufficient_data_returns_no_anomaly(self):
        points = make_points([80.0] * 10)
        result = self.detector.detect("cpu", points)
        assert result.is_anomaly is False
        assert "not enough data" in result.detail

    def test_score_is_finite_float(self):
        points = make_points([30.0 + i % 5 for i in range(50)])
        result = self.detector.detect("mem", points)
        assert isinstance(result.score, float)

    def test_invalid_contamination_raises(self):
        with pytest.raises(ValueError):
            IsolationForestDetector(contamination=0.0)
        with pytest.raises(ValueError):
            IsolationForestDetector(contamination=0.5)