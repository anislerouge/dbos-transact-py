import httpx
import pytest
from dbos_dash.app import create_app
from dbos_dash.config import DashConfig


@pytest.fixture
def config():
    return DashConfig(
        app_name="test-app",
        database_url="postgresql://postgres:admin@localhost:5432/test_db",
        serve_frontend=False,
    )


@pytest.fixture
def app(config):
    return create_app(config)


@pytest.fixture
async def client(app):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
