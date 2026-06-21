import pytest
from unittest.mock import AsyncMock, MagicMock
from app.detector.analysis_service import AnalysisService
from app.models import DetectionResult, DetectorKind, MetricPoint
from datetime import datetime, timezone


class MockDetector:
    def detect(self, metric_name, points):
        return DetectionResult(
            metric_name=metric_name,
            detector=DetectorKind.SIGMA,
            is_anomaly=False,
            score=0.5,
            detail="test"
        )


class MockPrometheusClient:
    async def fetch_range(self, metric, lookback):
        return [
            MetricPoint(timestamp=datetime.now(timezone.utc), value=50.0),
            MetricPoint(timestamp=datetime.now(timezone.utc), value=55.0),
        ]


@pytest.mark.asyncio
async def test_analysis_service_run():
    prometheus = MockPrometheusClient()
    detectors = [MockDetector()]
    service = AnalysisService(prometheus, detectors, ["cpu"], 3600)
    
    results = await service.run()
    assert len(results) == 1
    assert results[0].metric_name == "cpu"


@pytest.mark.asyncio
async def test_analysis_service_handles_empty_data():
    class EmptyPrometheus:
        async def fetch_range(self, metric, lookback):
            return []
    
    prometheus = EmptyPrometheus()
    detectors = [MockDetector()]
    service = AnalysisService(prometheus, detectors, ["cpu"], 3600)
    
    results = await service.run()
    assert len(results) == 0