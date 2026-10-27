import pytest

from config import env_flag, redis_service_settings


@pytest.mark.parametrize('value', ['1', 'true', 'TRUE', 'yes', 'on'])
def test_env_flag_accepts_enabled_values(monkeypatch, value):
    monkeypatch.setenv('FEATURE_FLAG', value)

    assert env_flag('FEATURE_FLAG') is True


@pytest.mark.parametrize('value', ['0', 'false', 'FALSE', 'no', 'off'])
def test_env_flag_accepts_disabled_values(monkeypatch, value):
    monkeypatch.setenv('FEATURE_FLAG', value)

    assert env_flag('FEATURE_FLAG', True) is False


def test_env_flag_uses_default_when_missing(monkeypatch):
    monkeypatch.delenv('FEATURE_FLAG', raising=False)

    assert env_flag('FEATURE_FLAG', True) is True


def test_env_flag_rejects_ambiguous_values(monkeypatch):
    monkeypatch.setenv('FEATURE_FLAG', 'sometimes')

    with pytest.raises(RuntimeError, match='Invalid boolean value'):
        env_flag('FEATURE_FLAG')


def test_enabled_redis_services_share_the_configured_url():
    settings = redis_service_settings(True, 'redis://cache:6379/2')

    assert settings == {
        'celery_broker_url': 'redis://cache:6379/2',
        'celery_result_backend': 'redis://cache:6379/2',
        'ratelimit_storage_uri': 'redis://cache:6379/2',
    }


def test_disabled_redis_services_use_in_process_backends():
    settings = redis_service_settings(False, 'redis://unavailable:6379/0')

    assert settings == {
        'celery_broker_url': 'memory://',
        'celery_result_backend': 'cache+memory://',
        'ratelimit_storage_uri': 'memory://',
    }


def test_app_startup_does_not_log_redis_credentials(monkeypatch, capsys):
    import app as app_module
    from config import TestingConfig

    redis_url = 'redis://:startup-log-canary@cache:6379/0'
    monkeypatch.setattr(TestingConfig, 'REDIS_ENABLED', True)
    monkeypatch.setattr(TestingConfig, 'REDIS_URL', redis_url)
    monkeypatch.setattr(TestingConfig, 'CELERY_BROKER_URL', redis_url)
    monkeypatch.setattr(TestingConfig, 'CELERY_RESULT_BACKEND', redis_url)
    monkeypatch.setattr(TestingConfig, 'RATELIMIT_STORAGE_URI', redis_url)
    monkeypatch.setattr(app_module, 'setup_database', lambda *_args, **_kwargs: None)
    monkeypatch.setattr(app_module.limiter, 'init_app', lambda *_args, **_kwargs: None)

    app_module.create_app('testing')

    output = capsys.readouterr()
    assert redis_url not in output.out + output.err
    assert 'startup-log-canary' not in output.out + output.err
    assert 'Redis Enabled: True' in output.out
