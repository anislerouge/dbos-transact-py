import json
import logging

from open_conductor.conductor import protocol as p
from open_conductor.conductor.executor_manager import ExecutorInfo, ExecutorManager
from starlette.websockets import WebSocket, WebSocketDisconnect

logger = logging.getLogger("open_conductor")


async def handle_executor_connection(
    websocket: WebSocket,
    app_name: str,
    conductor_key: str,
    manager: ExecutorManager,
    valid_api_keys: list[str],
) -> None:
    """Handle a WebSocket connection from a DBOS executor."""
    # Validate API key if configured
    if valid_api_keys and conductor_key not in valid_api_keys:
        await websocket.close(code=4003, reason="Invalid API key")
        return

    await websocket.accept()

    # Step 1: Send EXECUTOR_INFO request
    request_id = manager.new_request_id()
    info_request = p.ExecutorInfoRequest(
        type=p.MessageType.EXECUTOR_INFO,
        request_id=request_id,
    )
    await websocket.send_text(info_request.to_json())

    # Step 2: Wait for EXECUTOR_INFO response
    try:
        raw = await websocket.receive_text()
    except WebSocketDisconnect:
        logger.warning(f"Executor disconnected before sending info (app={app_name})")
        return

    info_response = p.ExecutorInfoResponse.from_json(raw)
    executor = ExecutorInfo(
        executor_id=info_response.executor_id,
        app_name=app_name,
        websocket=websocket,
        hostname=info_response.hostname,
        language=info_response.language,
        application_version=info_response.application_version,
        dbos_version=info_response.dbos_version,
    )

    await manager.register(executor)
    logger.info(
        f"Executor {executor.executor_id} connected for app '{app_name}' "
        f"(host={executor.hostname}, version={executor.application_version})"
    )

    # Step 3: Receive loop — every incoming message is a response to a command
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
                req_id = data.get("request_id")
                if req_id:
                    resolved = manager.resolve_response(req_id, raw)
                    if not resolved:
                        logger.warning(
                            f"No pending request for request_id={req_id} from executor {executor.executor_id}"
                        )
                else:
                    logger.warning(
                        f"Received message without request_id from executor {executor.executor_id}"
                    )
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON from executor {executor.executor_id}")
    except WebSocketDisconnect:
        logger.info(f"Executor {executor.executor_id} disconnected (app={app_name})")
    except Exception as e:
        logger.error(
            f"Error in WebSocket loop for executor {executor.executor_id}: {e}"
        )
    finally:
        await manager.unregister(executor)
