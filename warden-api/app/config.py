from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_path: str = "/data/warden.db"
    go2rtc_url: str = "http://go2rtc:1984"
    go2rtc_config_path: str = "/go2rtc-config/go2rtc.yaml"
    secret_key: str = "change-me-in-production"

    model_config = {"env_file": ".env"}


settings = Settings()
