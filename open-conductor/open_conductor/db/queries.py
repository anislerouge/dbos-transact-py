"""Direct SQL queries on DBOS system tables (read-only, optional).

These queries can be used when system_database_url is configured,
allowing Open Conductor to read workflow data directly from the DB
without going through WebSocket proxying.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine


def list_workflows_direct(
    engine: Engine,
    status: Optional[str] = None,
    name: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    query = """
        SELECT workflow_uuid, status, name, authenticated_user,
               output, error, executor_id, created_at, updated_at,
               application_version, queue_name
        FROM dbos.workflow_status
        WHERE 1=1
    """
    params: Dict[str, Any] = {"limit": limit, "offset": offset}

    if status is not None:
        query += " AND status = :status"
        params["status"] = status
    if name is not None:
        query += " AND name = :name"
        params["name"] = name

    query += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"

    with engine.connect() as conn:
        result = conn.execute(text(query), params)
        return [dict(row._mapping) for row in result]


def get_workflow_direct(engine: Engine, workflow_id: str) -> Optional[Dict[str, Any]]:
    query = """
        SELECT workflow_uuid, status, name, authenticated_user,
               output, error, executor_id, created_at, updated_at,
               application_version, queue_name
        FROM dbos.workflow_status
        WHERE workflow_uuid = :workflow_id
    """
    with engine.connect() as conn:
        result = conn.execute(text(query), {"workflow_id": workflow_id})
        row = result.first()
        if row is None:
            return None
        return dict(row._mapping)


def list_workflow_steps_direct(
    engine: Engine, workflow_id: str
) -> List[Dict[str, Any]]:
    query = """
        SELECT function_id, function_name, output, error,
               child_workflow_id, started_at_epoch_ms, completed_at_epoch_ms
        FROM dbos.operation_outputs
        WHERE workflow_uuid = :workflow_id
        ORDER BY function_id
    """
    with engine.connect() as conn:
        result = conn.execute(text(query), {"workflow_id": workflow_id})
        return [dict(row._mapping) for row in result]
