import pytest
from httpx import ASGITransport, AsyncClient
from open_conductor.conductor.executor_manager import ExecutorManager
from open_conductor.config import OpenConductorConfig
from open_conductor.server import deps
from open_conductor.server.app import create_app


@pytest.fixture
def config() -> OpenConductorConfig:
    return OpenConductorConfig(
        host="127.0.0.1",
        port=8080,
        api_keys=[],
        ws_timeout=5.0,
    )


@pytest.fixture
def manager(config: OpenConductorConfig) -> ExecutorManager:
    return ExecutorManager(ws_timeout=config.ws_timeout)


@pytest.fixture
def app(config: OpenConductorConfig):
    return create_app(config)


@pytest.fixture
async def client(app) -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
