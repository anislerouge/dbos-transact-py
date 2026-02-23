import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from starlette.websockets import WebSocket

logger = logging.getLogger("open_conductor")


@dataclass
class ExecutorInfo:
    executor_id: str
    app_name: str
    websocket: WebSocket
    hostname: Optional[str] = None
    language: Optional[str] = None
    application_version: Optional[str] = None
    dbos_version: Optional[str] = None


@dataclass
class PendingRequest:
    future: asyncio.Future[str]
    request_id: str


class ExecutorManager:
    """Tracks connected DBOS executors and routes commands to them."""

    def __init__(self, ws_timeout: float = 30.0) -> None:
        self._executors: Dict[str, List[ExecutorInfo]] = {}
        self._pending: Dict[str, PendingRequest] = {}
        self._round_robin: Dict[str, int] = {}
        self._ws_timeout = ws_timeout
        self._lock = asyncio.Lock()

    async def register(self, executor: ExecutorInfo) -> None:
        async with self._lock:
            if executor.app_name not in self._executors:
                self._executors[executor.app_name] = []
            self._executors[executor.app_name].append(executor)
            logger.info(
                f"Registered executor {executor.executor_id} for app '{executor.app_name}'"
            )

    async def unregister(self, executor: ExecutorInfo) -> None:
        async with self._lock:
            execs = self._executors.get(executor.app_name, [])
            self._executors[executor.app_name] = [
                e for e in execs if e.executor_id != executor.executor_id
            ]
            if not self._executors[executor.app_name]:
                del self._executors[executor.app_name]
                self._round_robin.pop(executor.app_name, None)
            logger.info(
                f"Unregistered executor {executor.executor_id} for app '{executor.app_name}'"
            )

    def get_apps(self) -> List[str]:
        return list(self._executors.keys())

    def get_executors(self, app_name: str) -> List[ExecutorInfo]:
        return list(self._executors.get(app_name, []))

    def _pick_executor(self, app_name: str) -> Optional[ExecutorInfo]:
        execs = self._executors.get(app_name, [])
        if not execs:
            return None
        idx = self._round_robin.get(app_name, 0) % len(execs)
        self._round_robin[app_name] = idx + 1
        return execs[idx]

    async def send_command(
        self, app_name: str, message_json: str, request_id: str
    ) -> str:
        """Send a command to an executor and wait for the response."""
        executor = self._pick_executor(app_name)
        if executor is None:
            raise ValueError(f"No executor connected for app '{app_name}'")

        loop = asyncio.get_event_loop()
        future: asyncio.Future[str] = loop.create_future()
        self._pending[request_id] = PendingRequest(future=future, request_id=request_id)

        try:
            await executor.websocket.send_text(message_json)
            return await asyncio.wait_for(future, timeout=self._ws_timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(
                f"Timeout waiting for response from executor (app='{app_name}', request_id='{request_id}')"
            )
        finally:
            self._pending.pop(request_id, None)

    def resolve_response(self, request_id: str, response_json: str) -> bool:
        """Resolve a pending request with the response from an executor."""
        pending = self._pending.get(request_id)
        if pending is None:
            return False
        if not pending.future.done():
            pending.future.set_result(response_json)
        return True

    @staticmethod
    def new_request_id() -> str:
        return str(uuid.uuid4())
