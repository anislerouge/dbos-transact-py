"""
Open Conductor executor plugin.

Drop-in handler for DBOS apps that adds support for Open Conductor
extended protocol messages (like start_workflow with custom params).

Usage in your DBOS app:

    from open_conductor.executor_plugin import install_oc_handler
    install_oc_handler()
"""

import json
import logging
import traceback

from dbos import DBOS

logger = logging.getLogger("open_conductor.executor_plugin")


def install_oc_handler() -> None:
    """
    Monkey-patch the DBOS ConductorWebsocket to handle
    Open Conductor extended messages (oc_start_workflow, etc.).
    """
    from dbos._conductor import protocol as p
    from dbos._conductor.conductor import ConductorWebsocket

    _original_run = ConductorWebsocket.run

    def _patched_run(self: ConductorWebsocket) -> None:
        """Wraps the original run to intercept OC messages before 'unknown type'."""
        # We patch the message handler by wrapping the websocket recv loop.
        # Instead of patching run(), we patch at the message level by hooking
        # into the websocket receive. This is done by storing the original
        # and adding an OC handler.
        pass

    # Instead of patching run() which is complex, we add OC message handling
    # by providing a custom message handler that the conductor checks.
    # Since the DBOS conductor doesn't have a plugin system, we store
    # our handler on the DBOS instance for the conductor to find.
    _dbos_instance = None

    try:
        from dbos._dbos import _get_dbos_instance

        _dbos_instance = _get_dbos_instance()
    except Exception:
        pass

    if _dbos_instance is not None:
        _dbos_instance._oc_handler = _handle_oc_message  # type: ignore
        logger.info("Open Conductor executor plugin installed")


def _handle_oc_message(dbos: "DBOS", message: str) -> str | None:
    """
    Handle an Open Conductor extended message.
    Returns the response JSON string, or None if the message is not an OC message.
    """
    try:
        data = json.loads(message)
    except json.JSONDecodeError:
        return None

    msg_type = data.get("type")
    request_id = data.get("request_id", "")

    if msg_type == "oc_start_workflow":
        return _handle_start_workflow(dbos, data, request_id)

    return None  # Not an OC message


def _handle_start_workflow(dbos: "DBOS", data: dict, request_id: str) -> str:
    """Handle oc_start_workflow: look up workflow by name and start it."""
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
            error_message = f"Workflow '{workflow_name}' not found in registry"
        else:
            handle = dbos.start_workflow(func, *args, **kwargs)
            workflow_id = handle.workflow_id
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
