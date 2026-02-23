import inspect
import json
import traceback
from typing import Any, List, Optional, get_args, get_origin

from dbos_dash.models import (
    StartWorkflowParams,
    StartWorkflowResponse,
    StepOutput,
    SuccessResponse,
    WorkflowOutput,
)
from fastapi import APIRouter, HTTPException, Query

from dbos import DBOS
from dbos._dbos import _get_or_create_dbos_registry
from dbos._sys_db import StepInfo, WorkflowStatus

router = APIRouter()


def _to_workflow_output(ws: WorkflowStatus) -> WorkflowOutput:
    input_str = None
    if ws.input is not None:
        try:
            input_str = json.dumps(
                {"args": list(ws.input["args"]), "kwargs": ws.input["kwargs"]}
            )
        except Exception:
            input_str = str(ws.input)

    output_str = None
    if ws.output is not None:
        try:
            output_str = json.dumps(ws.output)
        except Exception:
            output_str = str(ws.output)

    error_str = None
    if ws.error is not None:
        error_str = str(ws.error)

    return WorkflowOutput(
        WorkflowUUID=ws.workflow_id,
        Status=(
            ws.status
            if isinstance(ws.status, str)
            else ws.status.value if ws.status else None
        ),
        WorkflowName=ws.name,
        WorkflowClassName=ws.class_name,
        WorkflowConfigName=ws.config_name,
        AuthenticatedUser=ws.authenticated_user,
        AssumedRole=ws.assumed_role,
        AuthenticatedRoles=(
            json.dumps(ws.authenticated_roles) if ws.authenticated_roles else None
        ),
        Input=input_str,
        Output=output_str,
        Error=error_str,
        CreatedAt=str(ws.created_at) if ws.created_at is not None else None,
        UpdatedAt=str(ws.updated_at) if ws.updated_at is not None else None,
        QueueName=ws.queue_name,
        ApplicationVersion=ws.app_version,
        ExecutorID=ws.executor_id,
        WorkflowTimeoutMS=(
            str(ws.workflow_timeout_ms) if ws.workflow_timeout_ms is not None else None
        ),
        WorkflowDeadlineEpochMS=(
            str(ws.workflow_deadline_epoch_ms)
            if ws.workflow_deadline_epoch_ms is not None
            else None
        ),
        DeduplicationID=ws.deduplication_id,
        Priority=str(ws.priority) if ws.priority is not None else None,
        QueuePartitionKey=ws.queue_partition_key,
        ForkedFrom=ws.forked_from,
        ParentWorkflowID=ws.parent_workflow_id,
        DequeuedAt=str(ws.dequeued_at) if ws.dequeued_at is not None else None,
    )


def _to_step_output(s: StepInfo) -> StepOutput:
    output_str = None
    if s.get("output") is not None:
        try:
            output_str = json.dumps(s["output"])
        except Exception:
            output_str = str(s["output"])

    error_str = None
    if s.get("error") is not None:
        error_str = str(s["error"])

    return StepOutput(
        function_id=s["function_id"],
        function_name=s["function_name"],
        output=output_str,
        error=error_str,
        child_workflow_id=s.get("child_workflow_id"),
        started_at_epoch_ms=(
            str(s["started_at_epoch_ms"])
            if s.get("started_at_epoch_ms") is not None
            else None
        ),
        completed_at_epoch_ms=(
            str(s["completed_at_epoch_ms"])
            if s.get("completed_at_epoch_ms") is not None
            else None
        ),
    )


# --- Routes (order matters: literal paths before {workflow_id}) ---


def _annotation_to_json_schema(annotation: Any) -> dict:
    """Convert a Python type annotation to a simplified JSON schema."""
    if annotation is inspect.Parameter.empty or annotation is Any:
        return {}

    origin = get_origin(annotation)
    args = get_args(annotation)

    if annotation is str:
        return {"type": "string"}
    if annotation is int:
        return {"type": "integer"}
    if annotation is float:
        return {"type": "number"}
    if annotation is bool:
        return {"type": "boolean"}
    if annotation is list or origin is list:
        schema: dict = {"type": "array"}
        if args:
            schema["items"] = _annotation_to_json_schema(args[0])
        return schema
    if annotation is dict or origin is dict:
        schema = {"type": "object"}
        if args and len(args) == 2:
            schema["additionalProperties"] = _annotation_to_json_schema(args[1])
        return schema
    if origin is Optional or (
        origin is type(int | str) if hasattr(type(int | str), "__name__") else False
    ):
        # Optional[X] = Union[X, None]
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return _annotation_to_json_schema(non_none[0])

    # Fallback: return the type name
    type_name = getattr(annotation, "__name__", str(annotation))
    return {"type": type_name}


def _get_workflow_params(func: Any) -> list[dict]:
    """Extract parameter info from a workflow function signature."""
    sig = inspect.signature(func)
    params = []
    for name, param in sig.parameters.items():
        info: dict[str, Any] = {"name": name}

        if param.annotation is not inspect.Parameter.empty:
            info["type"] = _annotation_to_json_schema(param.annotation)
            # Also keep a human-readable type string
            info["type_hint"] = inspect.formatannotation(param.annotation)

        if param.default is not inspect.Parameter.empty:
            try:
                json.dumps(param.default)  # check serializable
                info["default"] = param.default
            except (TypeError, ValueError):
                info["default"] = str(param.default)

        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            info["variadic"] = "args"
        elif param.kind == inspect.Parameter.VAR_KEYWORD:
            info["variadic"] = "kwargs"

        params.append(info)
    return params


@router.get("/workflows/registry")
async def list_registered_workflows():
    registry = _get_or_create_dbos_registry()
    result = []
    for name, func in sorted(registry.workflow_info_map.items()):
        if name.startswith("<temp>"):
            continue
        result.append(
            {
                "name": name,
                "params": _get_workflow_params(func),
            }
        )
    return result


@router.post("/workflows/start", response_model=StartWorkflowResponse)
async def start_workflow(params: StartWorkflowParams):
    try:
        registry = _get_or_create_dbos_registry()
        func = registry.workflow_info_map.get(params.workflow_name)
        if func is None:
            return StartWorkflowResponse(
                error_message=f"Unknown workflow: {params.workflow_name}"
            )
        handle = DBOS.start_workflow(func, *params.args, **params.kwargs)
        return StartWorkflowResponse(workflow_id=handle.workflow_id)
    except Exception:
        return StartWorkflowResponse(error_message=traceback.format_exc())


@router.get("/workflows/queued", response_model=List[WorkflowOutput])
async def list_queued_workflows(
    status: Optional[str] = Query(None),
    name: Optional[str] = Query(None, alias="workflow_name"),
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
    limit: Optional[int] = Query(None),
    offset: Optional[int] = Query(None),
    sort_desc: bool = Query(False),
    load_input: bool = Query(False),
    load_output: bool = Query(False),
):
    workflows = await DBOS.list_queued_workflows_async(
        status=status,
        name=name,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
        sort_desc=sort_desc,
        load_input=load_input,
        load_output=load_output,
    )
    return [_to_workflow_output(ws) for ws in workflows]


@router.get("/workflows", response_model=List[WorkflowOutput])
async def list_workflows(
    status: Optional[str] = Query(None),
    name: Optional[str] = Query(None, alias="workflow_name"),
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
    limit: Optional[int] = Query(None),
    offset: Optional[int] = Query(None),
    sort_desc: bool = Query(False),
    load_input: bool = Query(False),
    load_output: bool = Query(False),
):
    workflows = await DBOS.list_workflows_async(
        status=status,
        name=name,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
        sort_desc=sort_desc,
        load_input=load_input,
        load_output=load_output,
    )
    return [_to_workflow_output(ws) for ws in workflows]


@router.get("/workflows/{workflow_id}", response_model=WorkflowOutput)
async def get_workflow(workflow_id: str):
    ws = await DBOS.get_workflow_status_async(workflow_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return _to_workflow_output(ws)


@router.get("/workflows/{workflow_id}/steps", response_model=List[StepOutput])
async def get_workflow_steps(workflow_id: str):
    steps = await DBOS.list_workflow_steps_async(workflow_id)
    return [_to_step_output(s) for s in steps]


@router.post("/workflows/{workflow_id}/cancel", response_model=SuccessResponse)
async def cancel_workflow(workflow_id: str):
    try:
        await DBOS.cancel_workflow_async(workflow_id)
        return SuccessResponse(success=True)
    except Exception as e:
        return SuccessResponse(success=False, error_message=str(e))


@router.post("/workflows/{workflow_id}/resume", response_model=SuccessResponse)
async def resume_workflow(workflow_id: str):
    try:
        await DBOS.resume_workflow_async(workflow_id)
        return SuccessResponse(success=True)
    except Exception as e:
        return SuccessResponse(success=False, error_message=str(e))


@router.post("/workflows/{workflow_id}/restart", response_model=SuccessResponse)
async def restart_workflow(workflow_id: str):
    try:
        await DBOS.fork_workflow_async(workflow_id, 1)
        return SuccessResponse(success=True)
    except Exception as e:
        return SuccessResponse(success=False, error_message=str(e))
