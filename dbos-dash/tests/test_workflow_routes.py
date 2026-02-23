from unittest.mock import MagicMock, patch

import pytest


def _make_workflow_status(**overrides):
    ws = MagicMock()
    ws.workflow_id = overrides.get("workflow_id", "wf-123")
    ws.status = overrides.get("status", "SUCCESS")
    ws.name = overrides.get("name", "test_workflow")
    ws.class_name = None
    ws.config_name = None
    ws.authenticated_user = None
    ws.assumed_role = None
    ws.authenticated_roles = None
    ws.input = overrides.get("input", None)
    ws.output = overrides.get("output", "result")
    ws.error = None
    ws.created_at = 1700000000000
    ws.updated_at = 1700000001000
    ws.queue_name = None
    ws.executor_id = None
    ws.app_version = None
    ws.workflow_timeout_ms = None
    ws.workflow_deadline_epoch_ms = None
    ws.deduplication_id = None
    ws.priority = None
    ws.queue_partition_key = None
    ws.forked_from = None
    ws.parent_workflow_id = None
    ws.dequeued_at = None
    return ws


@pytest.mark.asyncio
@patch("dbos_dash.routes.workflows.DBOS")
async def test_list_workflows(mock_dbos, client):
    mock_dbos.list_workflows.return_value = [_make_workflow_status()]
    resp = await client.get("/api/v1/workflows?limit=10&sort_desc=true")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["WorkflowUUID"] == "wf-123"
    assert data[0]["Status"] == "SUCCESS"


@pytest.mark.asyncio
@patch("dbos_dash.routes.workflows.DBOS")
async def test_get_workflow(mock_dbos, client):
    mock_dbos.get_workflow_status.return_value = _make_workflow_status()
    resp = await client.get("/api/v1/workflows/wf-123")
    assert resp.status_code == 200
    assert resp.json()["WorkflowUUID"] == "wf-123"


@pytest.mark.asyncio
@patch("dbos_dash.routes.workflows.DBOS")
async def test_get_workflow_not_found(mock_dbos, client):
    mock_dbos.get_workflow_status.return_value = None
    resp = await client.get("/api/v1/workflows/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
@patch("dbos_dash.routes.workflows.DBOS")
async def test_cancel_workflow(mock_dbos, client):
    resp = await client.post("/api/v1/workflows/wf-123/cancel")
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    mock_dbos.cancel_workflow.assert_called_once_with("wf-123")


@pytest.mark.asyncio
@patch("dbos_dash.routes.workflows.DBOS")
async def test_resume_workflow(mock_dbos, client):
    resp = await client.post("/api/v1/workflows/wf-123/resume")
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    mock_dbos.resume_workflow.assert_called_once_with("wf-123")


@pytest.mark.asyncio
@patch("dbos_dash.routes.workflows.DBOS")
async def test_restart_workflow(mock_dbos, client):
    resp = await client.post("/api/v1/workflows/wf-123/restart")
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    mock_dbos.fork_workflow.assert_called_once_with("wf-123", 1)


@pytest.mark.asyncio
@patch("dbos_dash.routes.workflows.DBOS")
async def test_get_workflow_steps(mock_dbos, client):
    mock_dbos.list_workflow_steps.return_value = [
        {
            "function_id": 1,
            "function_name": "step_one",
            "output": "ok",
            "error": None,
            "child_workflow_id": None,
            "started_at_epoch_ms": 1700000000000,
            "completed_at_epoch_ms": 1700000000100,
        }
    ]
    resp = await client.get("/api/v1/workflows/wf-123/steps")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["function_name"] == "step_one"


@pytest.mark.asyncio
@patch("dbos_dash.routes.workflows.DBOS")
async def test_list_queued_workflows(mock_dbos, client):
    mock_dbos.list_queued_workflows.return_value = [
        _make_workflow_status(status="ENQUEUED")
    ]
    resp = await client.get("/api/v1/workflows/queued")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["Status"] == "ENQUEUED"
