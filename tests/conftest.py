import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import Config  # noqa: E402


@pytest.fixture(scope="session")
def app():
    tmp = tempfile.mkdtemp()

    class TestConfig(Config):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(tmp, "test.db").replace("\\", "/")
        OPENAI_API_KEY = ""
        LOAD_DEMO_DATA = True

    from yatrasathi import create_app
    application = create_app(TestConfig)
    yield application


@pytest.fixture(scope="session")
def engine(app):
    from yatrasathi.ai.engine import get_engine
    with app.app_context():
        return get_engine()


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, email="aishwarya@yatrasathi.in", password="user123"):
    return client.post("/login", data={"email": email, "password": password})
