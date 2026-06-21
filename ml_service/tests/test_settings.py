from app.settings import Settings


def test_settings_defaults():
    settings = Settings()
    assert settings.prometheus_url == "http://prometheus:9090"
    assert settings.lookback_seconds == 3600
    assert settings.worker_interval_seconds == 60
    assert settings.sigma_threshold == 3.0


def test_settings_custom_values():
    settings = Settings(
        prometheus_url="http://custom:9090",
        lookback_seconds=1800,
        sigma_threshold=2.5,
    )
    assert settings.prometheus_url == "http://custom:9090"
    assert settings.lookback_seconds == 1800
    assert settings.sigma_threshold == 2.5