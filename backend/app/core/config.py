from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "GIB Mobile Threat Intelligence Reporter"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./data/gib_mobile.db"
    group_ib_base_url: str = "https://tap.group-ib.com/api/v2/"
    group_ib_username: str | None = None
    group_ib_api_token: SecretStr | None = None
    group_ib_latest_lookback_days: int = 30
    request_timeout_seconds: float = 30.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def validate_runtime(self) -> None:
        if not 1 <= self.group_ib_latest_lookback_days <= 30:
            raise ValueError("GROUP_IB_LATEST_LOOKBACK_DAYS must be between 1 and 30.")
        if self.request_timeout_seconds <= 0:
            raise ValueError("REQUEST_TIMEOUT_SECONDS must be greater than zero.")


settings = Settings()
