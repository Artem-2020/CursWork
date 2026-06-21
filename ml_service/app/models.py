from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone


class DetectorKind(str, Enum):
    """Identifies which algorithm produced a result."""

    SIGMA = "sigma"
    ISOLATION_FOREST = "isolation_forest"


@dataclass(frozen=True)
class MetricPoint:
    """A single timestamped value from Prometheus."""

    timestamp: datetime
    value: float


@dataclass(frozen=True)
class DetectionResult:
    """
    Outcome of one detector run for a single metric.

    is_anomaly=True means the detector considers the latest window abnormal.
    score carries the raw detector signal (z-score or IF anomaly score).
    """

    metric_name: str
    detector: DetectorKind
    is_anomaly: bool
    score: float
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    detail: str = ""
