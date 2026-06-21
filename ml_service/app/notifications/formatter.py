from datetime import datetime, timezone

from app.models import DetectionResult

_METRIC_EMOJI: dict[str, str] = {
    "server_agent_cpu_usage_percent":    "🔥",
    "server_agent_memory_usage_percent": "🧠",
    "server_agent_disk_usage_percent":   "💾",
}

_DEFAULT_EMOJI = "⚠️"


def format_alert(
    result: DetectionResult,
    now: datetime | None = None,
) -> str:
    """
    Build a Telegram HTML message for an anomaly detection result.

    `now` is injectable for deterministic testing. When omitted,
    current UTC time is used.

    Example output:
        🔥 <b>ANOMALY DETECTED</b>

        Metric:   server_agent_cpu_usage_percent
        Detector: sigma
        Score:    4.2100
        Detail:   z=4.21, threshold=3.0, mean=45.30, std=8.12
        Time:     2024-05-01 14:32:01 UTC
    """
    if now is None:
        now = datetime.now(tz=timezone.utc)

    emoji = _METRIC_EMOJI.get(result.metric_name, _DEFAULT_EMOJI)
    time_str = now.strftime("%Y-%m-%d %H:%M:%S UTC")

    return (
        f"{emoji} <b>ANOMALY DETECTED</b>\n\n"
        f"Metric:   <code>{result.metric_name}</code>\n"
        f"Detector: <code>{result.detector.value}</code>\n"
        f"Score:    <code>{result.score:.4f}</code>\n"
        f"Detail:   {result.detail}\n"
        f"Time:     {time_str}"
    )
