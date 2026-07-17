from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    port: int = 8080
    max_attempts: int = 3


def get_settings() -> Settings:
    return Settings()
