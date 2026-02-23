import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from open_conductor.conductor.executor_manager import ExecutorInfo, ExecutorManager


def _make_executor(executor_id: str, app_name: str = "test-app") -> ExecutorInfo:
    ws = AsyncMock()
    return ExecutorInfo(
        executor_id=executor_id,
        app_name=app_name,
        websocket=ws,
        hostname="localhost",
        language="python",
        application_version="1.0",
        dbos_version="0.1.0",
    )


@pytest.mark.asyncio
async def test_register_and_unregister():
    mgr = ExecutorManager()
    ex = _make_executor("exec-1")

    await mgr.register(ex)
    assert "test-app" in mgr.get_apps()
    assert len(mgr.get_executors("test-app")) == 1

    await mgr.unregister(ex)
    assert "test-app" not in mgr.get_apps()
    assert len(mgr.get_executors("test-app")) == 0


@pytest.mark.asyncio
async def test_round_robin():
    mgr = ExecutorManager()
    ex1 = _make_executor("exec-1")
    ex2 = _make_executor("exec-2")

    await mgr.register(ex1)
    await mgr.register(ex2)

    picked = mgr._pick_executor("test-app")
    assert picked is not None
    first_id = picked.executor_id

    picked = mgr._pick_executor("test-app")
    assert picked is not None
    second_id = picked.executor_id

    assert first_id != second_id


@pytest.mark.asyncio
async def test_send_command_timeout():
    mgr = ExecutorManager(ws_timeout=0.1)
    ex = _make_executor("exec-1")
    # Make send_text a no-op (never resolves the future)
    ex.websocket.send_text = AsyncMock()

    await mgr.register(ex)

    with pytest.raises(TimeoutError):
        await mgr.send_command("test-app", '{"test": true}', "req-1")


@pytest.mark.asyncio
async def test_send_command_success():
    mgr = ExecutorManager(ws_timeout=5.0)
    ex = _make_executor("exec-1")

    async def fake_send(text):
        # Simulate the executor responding immediately
        await asyncio.sleep(0.01)
        mgr.resolve_response("req-1", '{"success": true}')

    ex.websocket.send_text = fake_send
    await mgr.register(ex)

    result = await mgr.send_command("test-app", '{"test": true}', "req-1")
    assert result == '{"success": true}'


@pytest.mark.asyncio
async def test_send_command_no_executor():
    mgr = ExecutorManager()
    with pytest.raises(ValueError, match="No executor connected"):
        await mgr.send_command("nonexistent-app", "{}", "req-1")


@pytest.mark.asyncio
async def test_resolve_unknown_request():
    mgr = ExecutorManager()
    assert mgr.resolve_response("unknown-id", "{}") is False
