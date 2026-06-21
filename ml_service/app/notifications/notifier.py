import logging
from dataclasses import dataclass
from typing import Protocol

import httpx

logger = logging.getLogger(__name__)

_TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


@dataclass(frozen=True)
class TelegramConfig:
    """
    Credentials for Telegram Bot API.
    Populated from environment variables via Settings — never hardcoded.
    """
    bot_token: str
    chat_id: str


class NotifierProtocol(Protocol):
    """
    Abstraction for anything that can deliver an alert message.

    AlertService depends on this Protocol, not on TelegramNotifier directly.
    Any object with async send(text: str) -> bool satisfies it —
    including test doubles — without inheriting from a base class.
    """

    async def send(self, text: str) -> bool:
        """
        Deliver `text` to the recipient.
        Returns True on success, False on any error. Never raises.
        """
        ...


class TelegramNotifier:
    """
    Sends HTML-formatted messages to a Telegram chat via Bot API.

    Single responsibility: HTTP call to Telegram.
    No detection logic, no message formatting — those live elsewhere.
    """

    def __init__(self, config: TelegramConfig, http_client: httpx.AsyncClient) -> None:
        self._config = config
        self._http = http_client
        self._url = _TELEGRAM_API.format(token=config.bot_token)

    async def send(self, text: str) -> bool:
        """
        POST `text` to the configured Telegram chat.
        Returns True on success, False on HTTP or network error. Never raises.
        """
        payload = {
            "chat_id": self._config.chat_id,
            "text": text,
            "parse_mode": "HTML",
        }

        try:
            response = await self._http.post(self._url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info("telegram alert sent (chat_id=%s)", self._config.chat_id)
            return True
        except httpx.HTTPStatusError as exc:
            logger.error(
                "telegram API error: status=%d body=%s",
                exc.response.status_code,
                exc.response.text[:200],
            )
            return False
        except httpx.HTTPError as exc:
            logger.error("telegram network error: %s", exc)
            return False
