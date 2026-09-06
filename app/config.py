from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NEPSE Investment Analysis API"
    app_env: str = "local"
    database_url: str = "sqlite:///./nepse.db"
    cors_origins: str = "*"
    methodology_version: str = "1.0"

    # Live-price upstream: "sharesansar" (default, scrapes the full universe from
    # sharesansar.com) or "nepse_unofficial" (community REST API, unreliable).
    # Admin endpoint accepts ?provider=... to override per-call for testing.
    nepse_upstream: str = "sharesansar"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


settings = Settings()
