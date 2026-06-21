import pytest
from unittest.mock import AsyncMock, MagicMock, create_autospec
import httpx

from app.prometheus.client import PrometheusClient


class TestPrometheusClientParse:
    """Тесты для статического метода _parse — без HTTP."""

    def test_parses_valid_payload(self) -> None:
        payload = {
            "data": {
                "result": [
                    {
                        "values": [
                            [1_700_000_000.0, "42.5"],
                            [1_700_000_015.0, "43.1"],
                        ]
                    }
                ]
            }
        }
        points = PrometheusClient._parse(payload)

        assert len(points) == 2
        assert points[0].value == 42.5
        assert points[1].value == 43.1
        assert points[0].timestamp < points[1].timestamp

    def test_empty_result_returns_empty_list(self) -> None:
        payload = {"data": {"result": []}}
        assert PrometheusClient._parse(payload) == []

    def test_missing_data_key_returns_empty_list(self) -> None:
        assert PrometheusClient._parse({}) == []

    def test_malformed_value_is_skipped(self) -> None:
        payload = {
            "data": {
                "result": [
                    {
                        "values": [
                            [1_700_000_000.0, "not_a_number"],
                            [1_700_000_015.0, "55.0"],
                        ]
                    }
                ]
            }
        }
        points = PrometheusClient._parse(payload)
        assert len(points) == 1
        assert points[0].value == 55.0


@pytest.mark.asyncio
class TestPrometheusClientFetchRange:
    """Тесты для fetch_range — HTTP вызовы через мок."""

    async def test_fetch_range_http_error(self):
        """При HTTP ошибке возвращается пустой список."""
        mock_client = create_autospec(httpx.AsyncClient)
        mock_client.get = AsyncMock(side_effect=httpx.HTTPError("Connection error"))

        client = PrometheusClient("http://test:9090", mock_client)
        points = await client.fetch_range("test_metric", 60)

        assert points == []
        mock_client.get.assert_called_once()

    async def test_fetch_range_empty_result(self):
        """При пустом результате от Prometheus возвращается пустой список."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"result": []}}
        mock_response.raise_for_status = MagicMock()

        mock_client = create_autospec(httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        client = PrometheusClient("http://test:9090", mock_client)
        points = await client.fetch_range("test_metric", 60)

        assert points == []
        mock_client.get.assert_called_once()

    async def test_fetch_range_success(self):
        """Успешный запрос возвращает распарсенные MetricPoint."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "result": [
                    {
                        "values": [
                            [1_700_000_000.0, "42.5"],
                            [1_700_000_015.0, "43.1"],
                        ]
                    }
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = create_autospec(httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        client = PrometheusClient("http://prometheus:9090", mock_client)
        points = await client.fetch_range("test_metric", 60)

        assert len(points) == 2
        assert points[0].value == 42.5
        mock_client.get.assert_called_once()

    async def test_fetch_range_http_status_error(self):
        """HTTPStatusError (4xx/5xx) тоже возвращает пустой список."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404", request=MagicMock(), response=MagicMock()
        )
        mock_client = create_autospec(httpx.AsyncClient)
        mock_client.get = AsyncMock(return_value=mock_response)

        client = PrometheusClient("http://test:9090", mock_client)
        points = await client.fetch_range("test_metric", 60)

        assert points == []