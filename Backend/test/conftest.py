import os
import sys
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import create_app

@pytest.fixture(scope="session")
def app():
    """
    建立 Flask app（Testing 模式）。
    工廠模式的 create_app() 通常可以吃 config name 或直接從 env 讀取。
    """
    os.environ["FLASK_ENV"] = "testing"
    os.environ["APP_ENV"] = "testing"
    
    app = create_app(config_name="testing")
    return app


@pytest.fixture()
def client(app):
    return app.test_client()
