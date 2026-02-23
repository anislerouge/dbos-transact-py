"""
Open Conductor executor handler.

Standalone WebSocket handler that DBOS apps can use to support
Open Conductor extended protocol (like starting workflows with custom params).

Usage:
    from open_conductor.executor_handler import handle_oc_message

    # In your custom conductor loop, call before the default handler:
    response = handle_oc_message(dbos, raw_message)
    if response is not None:
        websocket.send(response)
    else:
        # ... handle standard DBOS messages
"""

import json
import logging
import traceback
from typing import Optional

logger = logging.getLogger("open_conductor.executor_handler")


def handle_oc_message(dbos: "Any", message: str) -> Optional[str]:
    """
    Handle Open Conductor extended messages.
    Returns JSON response string, or None if not an OC message.
    """
    try:
        data = json.loads(message)
    except json.JSONDecodeError:
        return None

    msg_type = data.get("type")
    request_id = data.get("request_id", "")

    if msg_type == "oc_start_workflow":
        return _handle_start_workflow(dbos, data, request_id)

    return None


def _handle_start_workflow(dbos: "Any", data: dict, request_id: str) -> str:
    workflow_name = data.get("workflow_name", "")
    args = data.get("args", [])
    kwargs = data.get("kwargs", {})

    error_message = None
    workflow_id = None

    try:
        from dbos._dbos import _get_or_create_dbos_registry

        registry = _get_or_create_dbos_registry()

        func = registry.workflow_info_map.get(workflow_name)
        if func is None:
            error_message = f"Workflow '{workflow_name}' not found in registry. Available: {list(registry.workflow_info_map.keys())}"
        else:
            handle = dbos.start_workflow(func, *args, **kwargs)
            workflow_id = handle.workflow_id
            logger.info(f"Started workflow '{workflow_name}' -> {workflow_id}")
    except Exception:
        error_message = (
            f"Error starting workflow '{workflow_name}': {traceback.format_exc()}"
        )
        logger.error(error_message)

    return json.dumps(
        {
            "type": "oc_start_workflow",
            "request_id": request_id,
            "workflow_id": workflow_id,
            "error_message": error_message,
        }
    )
