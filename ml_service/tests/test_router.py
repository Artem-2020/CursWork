import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

from app.main import create_app
from app.settings import Settings
from app.detector.analysis_service import AnalysisService
from app.models import DetectionResult, DetectorKind
from datetime import datetime, timezone


class MockAnalysisService:
    """Mock для тестирования router без реального Prometheus."""
    
    async def run(self):
        return [
            DetectionResult(
                metric_name="test_metric",
                detector=DetectorKind.SIGMA,
                is_anomaly=False,
                score=0.5,
                checked_at=datetime.now(timezone.utc),
                detail="test"
            )
        ]


@pytest.fixture
def client():
    settings = Settings(
        prometheus_url="http://test:9090",
        lookback_seconds=60,
        worker_interval_seconds=3600,  # отключаем воркер для тестов
    )
    app = create_app(settings)
    
    # Подменяем реальный analysis_service моком
    mock_service = MockAnalysisService()
    app.state.analysis_service = mock_service
    
    return TestClient(app)


def test_healthz(client):
    response = client.get("/api/v1/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_endpoint_returns_200(client):
    response = client.post("/api/v1/analyze")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "anomalies" in data
    assert "results" in data
    assert isinstance(data["total"], int)
    assert isinstance(data["anomalies"], int)
    assert isinstance(data["results"], list)


def test_analyze_endpoint_returns_correct_structure(client):
    response = client.post("/api/v1/analyze")
    data = response.json()
    
    if len(data["results"]) > 0:
        result = data["results"][0]
        assert "metric_name" in result
        assert "detector" in result
        assert "is_anomaly" in result
        assert "score" in result
        assert "detail" in result