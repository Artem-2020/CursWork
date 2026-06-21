from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    All runtime settings are read from environment variables.
    Defaults are safe for local docker-compose usage.
    """

    # ── Prometheus ────────────────────────────────────────────────────────────
    prometheus_url: str = Field(
        default="http://prometheus:9090",
        description="Base URL of the Prometheus HTTP API.",
    )
    lookback_seconds: int = Field(
        default=3600,
        description="Length of the time window sent to the detector (seconds).",
    )
    worker_interval_seconds: int = Field(
        default=60,
        description="Interval between background analysis runs (seconds).",
    )

    # ── Detectors ─────────────────────────────────────────────────────────────
    min_data_points: int = Field(
        default=10,
        description="Detector refuses to predict with fewer points than this.",
    )
    sigma_threshold: float = Field(
        default=3.0,
        description="Number of standard deviations that triggers a 3σ alert.",
    )
    iforest_contamination: float = Field(
        default=0.05,
        description="Expected fraction of anomalies for Isolation Forest.",
    )

    # ── Telegram ──────────────────────────────────────────────────────────────
    telegram_bot_token: str = Field(
        default="",
        description="Telegram Bot API token. Leave empty to disable alerts.",
    )
    telegram_chat_id: str = Field(
        default="",
        description="Telegram chat/channel ID to send alerts to.",
    )
    alert_cooldown_minutes: int = Field(
        default=15,
        description="Minimum minutes between repeated alerts for the same metric.",
    )

    # ── General ───────────────────────────────────────────────────────────────
    log_level: str = Field(default="INFO")

    # Pydantic v2 — replaces deprecated inner class Config from v1.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @property
    def telegram_enabled(self) -> bool:
        """True only when both token and chat_id are provided."""
        return bool(self.telegram_bot_token and self.telegram_chat_id)
