from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    port: int = 8080


def get_settings() -> Settings:
    return Settings()
