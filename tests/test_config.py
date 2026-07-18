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


def test_settings_worker_pool_size_default(monkeypatch):
    monkeypatch.delenv("WORKER_POOL_SIZE", raising=False)
    assert Settings().worker_pool_size == 4


def test_settings_worker_pool_size_reads_env_var(monkeypatch):
    monkeypatch.setenv("WORKER_POOL_SIZE", "8")
    assert Settings().worker_pool_size == 8


def test_settings_mock_sleep_bounds_defaults(monkeypatch):
    monkeypatch.delenv("MOCK_MIN_SLEEP_SECONDS", raising=False)
    monkeypatch.delenv("MOCK_MAX_SLEEP_SECONDS", raising=False)
    settings = Settings()
    assert settings.mock_min_sleep_seconds == 2.0
    assert settings.mock_max_sleep_seconds == 10.0


def test_settings_mock_sleep_bounds_read_env_vars(monkeypatch):
    monkeypatch.setenv("MOCK_MIN_SLEEP_SECONDS", "0")
    monkeypatch.setenv("MOCK_MAX_SLEEP_SECONDS", "0.1")
    settings = Settings()
    assert settings.mock_min_sleep_seconds == 0.0
    assert settings.mock_max_sleep_seconds == 0.1


def test_settings_mock_failure_rate_default(monkeypatch):
    monkeypatch.delenv("MOCK_FAILURE_RATE", raising=False)
    assert Settings().mock_failure_rate == 0.2


def test_settings_mock_failure_rate_reads_env_var(monkeypatch):
    monkeypatch.setenv("MOCK_FAILURE_RATE", "0.5")
    assert Settings().mock_failure_rate == 0.5
