import asyncio
import logging
import logging.config
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import httpx
from fastapi import FastAPI

from app.alert_service import AlertService
from app.api.router import router
from app.detector import AnalysisService, IsolationForestDetector, SigmaDetector
from app.notifications import TelegramConfig, TelegramNotifier
from app.prometheus import AGENT_METRICS, PrometheusClient
from app.settings import Settings
from app.worker import AnalysisWorker


def create_app(settings: Settings | None = None) -> FastAPI:
    """
    Application factory.
    Accepts optional settings so tests can inject overrides without env vars.
    """
    if settings is None:
        settings = Settings()

    _configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        # ── startup ──────────────────────────────────────────────────────────
        http_client = httpx.AsyncClient()

        prometheus = PrometheusClient(settings.prometheus_url, http_client)

        detectors = [
            SigmaDetector(
                threshold=settings.sigma_threshold,
                min_points=settings.min_data_points,
            ),
            IsolationForestDetector(
                contamination=settings.iforest_contamination,
                min_points=settings.min_data_points * 2,
            ),
        ]

        analysis_service = AnalysisService(
            prometheus=prometheus,
            detectors=detectors,
            metrics=AGENT_METRICS,
            lookback_seconds=settings.lookback_seconds,
        )

        # Build AlertService only when Telegram credentials are present.
        # Without them the worker runs analysis_service directly —
        # results are logged but no Telegram message is sent.
        if settings.telegram_enabled:
            notifier = TelegramNotifier(
                config=TelegramConfig(
                    bot_token=settings.telegram_bot_token,
                    chat_id=settings.telegram_chat_id,
                ),
                http_client=http_client,
            )
            runnable = AlertService(
                analysis=analysis_service,
                notifier=notifier,
                cooldown_minutes=settings.alert_cooldown_minutes,
            )
            logging.getLogger(__name__).info("telegram alerts enabled")
        else:
            runnable = analysis_service
            logging.getLogger(__name__).warning(
                "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set — alerts disabled"
            )

        # analysis_service is stored separately so /analyze endpoint always
        # has direct access regardless of whether alerts are enabled.
        app.state.analysis_service = analysis_service

        worker = AnalysisWorker(runnable, settings.worker_interval_seconds)
        worker_task = asyncio.create_task(worker.run())

        yield

        # ── shutdown ─────────────────────────────────────────────────────────
        worker_task.cancel()
        await asyncio.gather(worker_task, return_exceptions=True)
        await http_client.aclose()

    app = FastAPI(
        title="Server Failure Prediction Service",
        description="Detects anomalies in server metrics using 3σ and Isolation Forest.",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.include_router(router)
    return app


def _configure_logging(level: str) -> None:
    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
            }
        },
        "root": {"level": level, "handlers": ["console"]},
    })
