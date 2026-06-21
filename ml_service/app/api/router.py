import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.detector.analysis_service import AnalysisService
from app.models import DetectionResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["analysis"])


# ── Response schemas ──────────────────────────────────────────────────────────

class DetectionResultSchema(BaseModel):
    metric_name: str
    detector: str
    is_anomaly: bool
    score: float
    checked_at: datetime
    detail: str

    model_config = {"from_attributes": True}


class AnalyzeResponse(BaseModel):
    total: int
    anomalies: int
    results: list[DetectionResultSchema]


# ── Dependency injection ──────────────────────────────────────────────────────

def get_analysis_service(request: Request) -> AnalysisService:
    """Extract AnalysisService from FastAPI app state."""
    return request.app.state.analysis_service


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/analyze", response_model=AnalyzeResponse, summary="Run analysis now")
async def analyze(service: AnalysisService = Depends(get_analysis_service)) -> AnalyzeResponse:
    """
    Trigger a full analysis cycle immediately.

    Useful for demos and manual checks — the background worker runs the
    same logic automatically on each interval tick.
    """
    results: list[DetectionResult] = await service.run()
    schemas = [DetectionResultSchema.model_validate(r) for r in results]

    return AnalyzeResponse(
        total=len(schemas),
        anomalies=sum(1 for r in schemas if r.is_anomaly),
        results=schemas,
    )


@router.get("/healthz", summary="Liveness probe")
async def healthz() -> dict:
    return {"status": "ok"}