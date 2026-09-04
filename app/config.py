from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NEPSE Investment Analysis API"
    app_env: str = "local"
    database_url: str = "sqlite:///./nepse.db"
    cors_origins: str = "*"
    methodology_version: str = "1.0"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


settings = Settings()
