import pytest
from datetime import datetime, timezone

from app.detector.sigma import SigmaDetector
from app.models import DetectorKind, MetricPoint


def make_points(values):
    """Helper: turn a list of floats into MetricPoint objects."""
    return [
        MetricPoint(
            timestamp=datetime.now(timezone.utc),
            value=v,
        )
        for v in values
    ]


class TestSigmaDetector:
    def setup_method(self):
        self.detector = SigmaDetector(threshold=3.0, min_points=5)

    def test_no_anomaly_on_stable_series(self):
        points = make_points([50.0] * 20)
        result = self.detector.detect("cpu", points)
        assert result.is_anomaly is False
        assert result.detector == DetectorKind.SIGMA

    def test_detects_spike(self):
        normal = [50.0] * 19
        spike = [200.0]
        points = make_points(normal + spike)
        result = self.detector.detect("cpu", points)
        assert result.score > 3.0
        assert result.is_anomaly == True  

    def test_insufficient_data_returns_no_anomaly(self):
        points = make_points([80.0, 82.0, 79.0])
        result = self.detector.detect("cpu", points)
        assert result.is_anomaly is False
        assert "not enough data" in result.detail

    def test_zero_std_does_not_raise(self):
        points = make_points([42.0] * 20)
        result = self.detector.detect("cpu", points)
        assert result.is_anomaly is False

    def test_result_carries_metric_name(self):
        points = make_points([10.0] * 10)
        result = self.detector.detect("disk", points)
        assert result.metric_name == "disk"

    @pytest.mark.parametrize("threshold", [1.0, 2.0, 5.0])
    def test_custom_threshold(self, threshold):
        detector = SigmaDetector(threshold=threshold, min_points=5)
        points = make_points([50.0] * 19 + [51.0])
        result = detector.detect("mem", points)
        assert result.detector == DetectorKind.SIGMA
        assert result.score >= 0