# config/base.py
import os
from datetime import timedelta


class BaseConfig:
    DEBUG = False
    TESTING = False

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 共用設定
    UPLOAD_FOLDER = "static/uploads/avatar"
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB

    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=30)
    JWT_TOKEN_LOCATION = ["headers", "cookies"]
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_COOKIE_SAMESITE = "Lax"
    JWT_COOKIE_SECURE = False
    JWT_REFRESH_COOKIE_PATH = "/api/refresh"
    JWT_REFRESH_CSRF_COOKIE_PATH = "/"

    SUPERADMIN_EMAIL = os.environ.get("SUPERADMIN_EMAIL")

    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:4200")
    API_URL = os.environ.get("API_URL", "http://localhost:5000")

    CELERY_BROKER_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    CELERY_RESULT_BACKEND = os.environ.get("REDIS_URL", "redis://redis:6379/0")

    RATELIMIT_STORAGE_URI = os.environ.get("REDIS_URL", "memory://")
    RATELIMIT_STRATEGY = "fixed-window"
    RATELIMIT_HEADERS_ENABLED = True

    @classmethod
    def init_app(cls, app):
        if not app.config.get("JWT_SECRET_KEY") and not app.config.get("TESTING"):
            raise RuntimeError("JWT_SECRET_KEY must be set")

class DevelopmentConfig(BaseConfig):
    DEBUG = True
    TESTING = False

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or (
        f"postgresql+psycopg2://"
        f"{os.environ.get('DB_USER', 'postgres')}:"
        f"{os.environ.get('DB_PASSWORD', '')}@"
        f"{os.environ.get('DB_SERVER', 'localhost')}:"
        f"{os.environ.get('DB_PORT', '5432')}/"
        f"{os.environ.get('DB_NAME', 'jackandbeanstalks')}"
    )

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": int(os.environ.get("DB_POOL_SIZE", 10)),
        "max_overflow": int(os.environ.get("DB_MAX_OVERFLOW", 20)),
        "pool_timeout": int(os.environ.get("DB_POOL_TIMEOUT", 30)),
        "pool_recycle": int(os.environ.get("DB_POOL_RECYCLE", 3600)),
        "pool_pre_ping": os.environ.get("DB_POOL_PRE_PING", "true").lower() == "true",
        "echo": os.environ.get("DB_ECHO", "false").lower() == "true",
    }


class TestingConfig(BaseConfig):
    DEBUG = False
    TESTING = True

    # 測試建議用獨立 sqlite
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "TEST_DATABASE_URL",
        "sqlite:///:memory:"
    )

    # 測試環境通常不需要複雜 pool 設定
    SQLALCHEMY_ENGINE_OPTIONS = {
        "echo": False
    }

    RATELIMIT_STORAGE_URI = "memory://"


class ProductionConfig(BaseConfig):
    DEBUG = False
    TESTING = False
    TRUSTED_PROXY_HOPS = 1
    JWT_COOKIE_SECURE = True

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or (
        f"postgresql+psycopg2://"
        f"{os.environ.get('DB_USER', 'postgres')}:"
        f"{os.environ.get('DB_PASSWORD', '')}@"
        f"{os.environ.get('DB_SERVER', 'localhost')}:"
        f"{os.environ.get('DB_PORT', '5432')}/"
        f"{os.environ.get('DB_NAME', 'jackandbeanstalks')}"
    )

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": int(os.environ.get("DB_POOL_SIZE", 10)),
        "max_overflow": int(os.environ.get("DB_MAX_OVERFLOW", 20)),
        "pool_timeout": int(os.environ.get("DB_POOL_TIMEOUT", 30)),
        "pool_recycle": int(os.environ.get("DB_POOL_RECYCLE", 3600)),
        "pool_pre_ping": os.environ.get("DB_POOL_PRE_PING", "true").lower() == "true",
        "echo": os.environ.get("DB_ECHO", "false").lower() == "true",
    }
