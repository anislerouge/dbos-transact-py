import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from open_conductor.conductor.executor_manager import ExecutorInfo, ExecutorManager
from open_conductor.config import OpenConductorConfig
from open_conductor.server import deps
from open_conductor.server.app import create_app


@pytest.fixture
def mock_app():
    config = OpenConductorConfig(api_keys=[], ws_timeout=5.0)
    app = create_app(config)
    return app


@pytest.fixture
async def client(mock_app):
    transport = ASGITransport(app=mock_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["connected_apps"] == 0


@pytest.mark.asyncio
async def test_list_apps_empty(client: AsyncClient):
    resp = await client.get("/api/v1/apps")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_executors_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/apps/nonexistent/executors")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_apps_with_executor(client: AsyncClient):
    # Register a mock executor
    manager = deps.get_executor_manager()
    ex = ExecutorInfo(
        executor_id="exec-1",
        app_name="my-app",
        websocket=AsyncMock(),
        hostname="localhost",
        language="python",
        application_version="1.0",
    )
    await manager.register(ex)

    resp = await client.get("/api/v1/apps")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "my-app"
    assert data[0]["executor_count"] == 1

    # Cleanup
    await manager.unregister(ex)


@pytest.mark.asyncio
async def test_cancel_workflow_no_executor(client: AsyncClient):
    resp = await client.post("/api/v1/apps/my-app/workflows/wf-1/cancel")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cancel_workflow_proxied(client: AsyncClient):
    manager = deps.get_executor_manager()

    # Mock executor that responds to cancel
    ws_mock = AsyncMock()

    async def fake_send(text):
        data = json.loads(text)
        response = json.dumps(
            {
                "type": "cancel",
                "request_id": data["request_id"],
                "success": True,
                "error_message": None,
            }
        )
        manager.resolve_response(data["request_id"], response)

    ws_mock.send_text = fake_send

    ex = ExecutorInfo(
        executor_id="exec-1",
        app_name="my-app",
        websocket=ws_mock,
    )
    await manager.register(ex)

    resp = await client.post("/api/v1/apps/my-app/workflows/wf-1/cancel")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True

    await manager.unregister(ex)


@pytest.mark.asyncio
async def test_list_workflows_proxied(client: AsyncClient):
    manager = deps.get_executor_manager()
    ws_mock = AsyncMock()

    async def fake_send(text):
        data = json.loads(text)
        response = json.dumps(
            {
                "type": "list_workflows",
                "request_id": data["request_id"],
                "output": [
                    {
                        "WorkflowUUID": "wf-123",
                        "Status": "SUCCESS",
                        "WorkflowName": "test_wf",
                    }
                ],
                "error_message": None,
            }
        )
        manager.resolve_response(data["request_id"], response)

    ws_mock.send_text = fake_send

    ex = ExecutorInfo(executor_id="exec-1", app_name="my-app", websocket=ws_mock)
    await manager.register(ex)

    resp = await client.get("/api/v1/apps/my-app/workflows")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["WorkflowUUID"] == "wf-123"

    await manager.unregister(ex)
