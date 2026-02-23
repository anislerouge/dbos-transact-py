import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from open_conductor.conductor import protocol as p
from open_conductor.conductor.executor_manager import ExecutorManager
from open_conductor.conductor.websocket import handle_executor_connection


class FakeWebSocket:
    """Simulates a Starlette WebSocket for testing."""

    def __init__(self, messages: list[str]):
        self._messages = list(messages)
        self._sent: list[str] = []
        self._accepted = False
        self._closed = False
        self._close_code = None
        self._close_reason = None

    async def accept(self):
        self._accepted = True

    async def close(self, code=1000, reason=""):
        self._closed = True
        self._close_code = code
        self._close_reason = reason

    async def send_text(self, data: str):
        self._sent.append(data)

    async def receive_text(self) -> str:
        if not self._messages:
            from starlette.websockets import WebSocketDisconnect

            raise WebSocketDisconnect(code=1000)
        return self._messages.pop(0)


@pytest.mark.asyncio
async def test_handshake_invalid_key():
    ws = FakeWebSocket([])
    mgr = ExecutorManager()

    await handle_executor_connection(ws, "my-app", "bad-key", mgr, ["valid-key"])
    assert ws._closed
    assert ws._close_code == 4003


@pytest.mark.asyncio
async def test_handshake_success():
    # Prepare the executor info response the "executor" will send
    info_resp = p.ExecutorInfoResponse(
        type=p.MessageType.EXECUTOR_INFO,
        request_id="will-be-replaced",
        executor_id="exec-1",
        application_version="1.0",
        hostname="test-host",
        language="python",
        dbos_version="0.1.0",
    )

    ws = FakeWebSocket([info_resp.to_json()])
    mgr = ExecutorManager()

    await handle_executor_connection(ws, "my-app", "key", mgr, [])

    # Should have accepted and sent EXECUTOR_INFO request
    assert ws._accepted
    assert len(ws._sent) == 1
    sent_msg = json.loads(ws._sent[0])
    assert sent_msg["type"] == p.MessageType.EXECUTOR_INFO

    # Executor registered then unregistered after disconnect
    assert "my-app" not in mgr.get_apps()


@pytest.mark.asyncio
async def test_response_routing():
    """Test that responses from the executor resolve pending futures."""
    mgr = ExecutorManager(ws_timeout=5.0)

    # The executor will send: info response, then a cancel response
    info_resp = p.ExecutorInfoResponse(
        type=p.MessageType.EXECUTOR_INFO,
        request_id="info-req",
        executor_id="exec-1",
        application_version="1.0",
        hostname="test-host",
        language="python",
        dbos_version="0.1.0",
    )
    cancel_resp = json.dumps(
        {
            "type": "cancel",
            "request_id": "cancel-req-1",
            "success": True,
            "error_message": None,
        }
    )

    ws = FakeWebSocket([info_resp.to_json(), cancel_resp])

    # Create a pending request that the cancel response will resolve
    loop = asyncio.get_event_loop()
    future: asyncio.Future[str] = loop.create_future()
    mgr._pending["cancel-req-1"] = MagicMock(future=future, request_id="cancel-req-1")

    await handle_executor_connection(ws, "my-app", "key", mgr, [])

    # The future should be resolved
    assert future.done()
    result = json.loads(future.result())
    assert result["success"] is True
