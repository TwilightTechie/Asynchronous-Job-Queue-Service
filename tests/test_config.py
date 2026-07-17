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


def test_settings_max_attempts_default(monkeypatch):
    monkeypatch.delenv("MAX_ATTEMPTS", raising=False)

    settings = Settings()

    assert settings.max_attempts == 3


def test_settings_max_attempts_reads_env_var(monkeypatch):
    monkeypatch.setenv("MAX_ATTEMPTS", "5")

    settings = Settings()

    assert settings.max_attempts == 5
