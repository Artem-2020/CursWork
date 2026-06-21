import logging
from datetime import datetime, timedelta, timezone

import httpx

from app.models import MetricPoint

logger = logging.getLogger(__name__)

# Prometheus metric names produced by the Go agent (block 1).
AGENT_METRICS: list[str] = [
    "server_agent_cpu_usage_percent",
    "server_agent_memory_usage_percent",
    "server_agent_disk_usage_percent",
]


class PrometheusClient:
    """
    Thin wrapper around the Prometheus HTTP API.

    Only responsibility: translate Prometheus JSON responses into
    lists of MetricPoint. No detection logic lives here.
    """

    def __init__(self, base_url: str, http_client: httpx.AsyncClient) -> None:
        self._base_url = base_url.rstrip("/")
        self._http = http_client

    async def fetch_range(
        self,
        metric: str,
        lookback_seconds: int,
        step: int = 15,
    ) -> list[MetricPoint]:
        """
        Fetch `metric` for the last `lookback_seconds` seconds.

        Returns an empty list when Prometheus returns no data (e.g. agent
        not yet scraped) so callers do not need to handle None.
        """
        now = datetime.now(tz=timezone.utc)
        start = now - timedelta(seconds=lookback_seconds)

        params = {
            "query": metric,
            "start": start.isoformat(),
            "end": now.isoformat(),
            "step": str(step),
        }

        try:
            response = await self._http.get(
                f"{self._base_url}/api/v1/query_range",
                params=params,
                timeout=10,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("prometheus request failed: %s", exc)
            return []

        return self._parse(response.json())

    @staticmethod
    def _parse(payload: dict) -> list[MetricPoint]:
        """Convert raw Prometheus JSON into MetricPoint objects."""
        results = payload.get("data", {}).get("result", [])
        if not results:
            return []

        points: list[MetricPoint] = []
        for series in results:
            for ts, val in series.get("values", []):
                try:
                    points.append(
                        MetricPoint(
                            timestamp=datetime.fromtimestamp(float(ts), tz=timezone.utc),
                            value=float(val),
                        )
                    )
                except (ValueError, TypeError) as exc:
                    logger.warning("skipping malformed data point: %s", exc)

        return sorted(points, key=lambda p: p.timestamp)
