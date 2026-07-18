from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    port: int = 8080
    max_attempts: int = 3
    worker_pool_size: int = 4
    mock_min_sleep_seconds: float = 2.0
    mock_max_sleep_seconds: float = 10.0
    mock_failure_rate: float = 0.2


def get_settings() -> Settings:
    return Settings()
