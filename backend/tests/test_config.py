import os

from app.core.config import Settings


def test_lookback_is_bounded():
    settings = Settings(group_ib_latest_lookback_days=30)
    settings.validate_runtime()


def test_secret_is_not_required_for_config_validation():
    settings = Settings(group_ib_latest_lookback_days=7)
    settings.validate_runtime()
