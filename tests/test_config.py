from app.config import Settings, get_settings


def test_settings_defaults(monkeypatch):
    monkeypatch.delenv("PORT", raising=False)

    settings = Settings()

    assert settings.port == 8080


def test_settings_reads_env_vars(monkeypatch):
    monkeypatch.setenv("PORT", "9090")

    settings = Settings()

    assert settings.port == 9090


def test_get_settings_returns_settings_instance():
    assert isinstance(get_settings(), Settings)
