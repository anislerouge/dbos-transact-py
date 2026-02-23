import json
from typing import List, Optional, Union

from fastapi import APIRouter, HTTPException, Query
from open_conductor.conductor import protocol as p
from open_conductor.conductor.executor_manager import ExecutorManager
from open_conductor.server.deps import get_executor_manager
from open_conductor.server.models import (
    ForkWorkflowParams,
    ImportWorkflowParams,
    ListWorkflowsParams,
    StartWorkflowParams,
)
from open_conductor.server.models import (
    StartWorkflowResponse as StartWorkflowResponseModel,
)
from open_conductor.server.models import StepOutput, SuccessResponse, WorkflowOutput

router = APIRouter(prefix="/api/v1/apps/{app_name}", tags=["workflows"])


async def _send_and_parse(
    manager: ExecutorManager, app_name: str, message: p.BaseMessage
) -> dict:
    """Send a protocol message and parse the JSON response."""
    try:
        raw = await manager.send_command(
            app_name, message.to_json(), message.request_id
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    return json.loads(raw)


@router.get("/workflows", response_model=List[WorkflowOutput])
async def list_workflows(
    app_name: str,
    workflow_name: Optional[str] = None,
    status: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    sort_desc: bool = False,
    load_input: bool = False,
    load_output: bool = False,
) -> List[WorkflowOutput]:
    manager = get_executor_manager()
    request_id = manager.new_request_id()
    body: p.ListWorkflowsBody = {
        "sort_desc": sort_desc,
        "load_input": load_input,
        "load_output": load_output,
        "queues_only": False,
    }
    if workflow_name is not None:
        body["workflow_name"] = workflow_name
    if status is not None:
        body["status"] = status
    if start_time is not None:
        body["start_time"] = start_time
    if end_time is not None:
        body["end_time"] = end_time
    if limit is not None:
        body["limit"] = limit
    if offset is not None:
        body["offset"] = offset

    msg = p.ListWorkflowsRequest(
        type=p.MessageType.LIST_WORKFLOWS,
        request_id=request_id,
        body=body,
    )
    data = await _send_and_parse(manager, app_name, msg)
    if data.get("error_message"):
        raise HTTPException(status_code=502, detail=data["error_message"])
    return [WorkflowOutput(**w) for w in data.get("output", [])]


@router.post("/workflows/start", response_model=StartWorkflowResponseModel)
async def start_workflow(
    app_name: str, params: StartWorkflowParams
) -> StartWorkflowResponseModel:
    """Start a new workflow by name with given arguments (Open Conductor extension)."""
    manager = get_executor_manager()
    request_id = manager.new_request_id()
    msg = p.StartWorkflowRequest(
        type=p.OpenConductorMessageType.START_WORKFLOW,
        request_id=request_id,
        workflow_name=params.workflow_name,
        args=params.args,
        kwargs=params.kwargs,
    )
    data = await _send_and_parse(manager, app_name, msg)
    return StartWorkflowResponseModel(
        workflow_id=data.get("workflow_id"),
        error_message=data.get("error_message"),
    )


@router.post("/workflows/import", response_model=SuccessResponse)
async def import_workflow(
    app_name: str, params: ImportWorkflowParams
) -> SuccessResponse:
    manager = get_executor_manager()
    request_id = manager.new_request_id()
    msg = p.ImportWorkflowRequest(
        type=p.MessageType.IMPORT_WORKFLOW,
        request_id=request_id,
        serialized_workflow=params.serialized_workflow,
    )
    data = await _send_and_parse(manager, app_name, msg)
    return SuccessResponse(
        success=data.get("success", False), error_message=data.get("error_message")
    )


@router.get("/workflows/{workflow_id}", response_model=Optional[WorkflowOutput])
async def get_workflow(app_name: str, workflow_id: str) -> Optional[WorkflowOutput]:
    manager = get_executor_manager()
    request_id = manager.new_request_id()
    msg = p.GetWorkflowRequest(
        type=p.MessageType.GET_WORKFLOW,
        request_id=request_id,
        workflow_id=workflow_id,
    )
    data = await _send_and_parse(manager, app_name, msg)
    if data.get("error_message"):
        raise HTTPException(status_code=502, detail=data["error_message"])
    output = data.get("output")
    if output is None:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
    return WorkflowOutput(**output)


@router.get("/workflows/{workflow_id}/steps", response_model=List[StepOutput])
async def list_steps(app_name: str, workflow_id: str) -> List[StepOutput]:
    manager = get_executor_manager()
    request_id = manager.new_request_id()
    msg = p.ListStepsRequest(
        type=p.MessageType.LIST_STEPS,
        request_id=request_id,
        workflow_id=workflow_id,
    )
    data = await _send_and_parse(manager, app_name, msg)
    if data.get("error_message"):
        raise HTTPException(status_code=502, detail=data["error_message"])
    return [StepOutput(**s) for s in data.get("output", []) or []]


@router.post("/workflows/{workflow_id}/cancel", response_model=SuccessResponse)
async def cancel_workflow(app_name: str, workflow_id: str) -> SuccessResponse:
    manager = get_executor_manager()
    request_id = manager.new_request_id()
    msg = p.CancelRequest(
        type=p.MessageType.CANCEL,
        request_id=request_id,
        workflow_id=workflow_id,
    )
    data = await _send_and_parse(manager, app_name, msg)
    return SuccessResponse(
        success=data.get("success", False), error_message=data.get("error_message")
    )


@router.post("/workflows/{workflow_id}/resume", response_model=SuccessResponse)
async def resume_workflow(app_name: str, workflow_id: str) -> SuccessResponse:
    manager = get_executor_manager()
    request_id = manager.new_request_id()
    msg = p.ResumeRequest(
        type=p.MessageType.RESUME,
        request_id=request_id,
        workflow_id=workflow_id,
    )
    data = await _send_and_parse(manager, app_name, msg)
    return SuccessResponse(
        success=data.get("success", False), error_message=data.get("error_message")
    )


@router.post("/workflows/{workflow_id}/restart", response_model=SuccessResponse)
async def restart_workflow(app_name: str, workflow_id: str) -> SuccessResponse:
    manager = get_executor_manager()
    request_id = manager.new_request_id()
    msg = p.RestartRequest(
        type=p.MessageType.RESTART,
        request_id=request_id,
        workflow_id=workflow_id,
    )
    data = await _send_and_parse(manager, app_name, msg)
    return SuccessResponse(
        success=data.get("success", False), error_message=data.get("error_message")
    )


@router.post("/workflows/{workflow_id}/fork", response_model=SuccessResponse)
async def fork_workflow(
    app_name: str, workflow_id: str, params: ForkWorkflowParams
) -> SuccessResponse:
    manager = get_executor_manager()
    request_id = manager.new_request_id()
    body: p.ForkWorkflowBody = {
        "workflow_id": workflow_id,
        "start_step": params.start_step,
        "application_version": params.application_version,
        "new_workflow_id": params.new_workflow_id,
    }
    msg = p.ForkWorkflowRequest(
        type=p.MessageType.FORK_WORKFLOW,
        request_id=request_id,
        body=body,
    )
    data = await _send_and_parse(manager, app_name, msg)
    new_id = data.get("new_workflow_id")
    err = data.get("error_message")
    return SuccessResponse(success=new_id is not None, error_message=err)


@router.delete("/workflows/{workflow_id}", response_model=SuccessResponse)
async def delete_workflow(
    app_name: str, workflow_id: str, delete_children: bool = False
) -> SuccessResponse:
    manager = get_executor_manager()
    request_id = manager.new_request_id()
    msg = p.DeleteRequest(
        type=p.MessageType.DELETE,
        request_id=request_id,
        workflow_id=workflow_id,
        delete_children=delete_children,
    )
    data = await _send_and_parse(manager, app_name, msg)
    return SuccessResponse(
        success=data.get("success", False), error_message=data.get("error_message")
    )


@router.get("/queued-workflows", response_model=List[WorkflowOutput])
async def list_queued_workflows(
    app_name: str,
    queue_name: Optional[str] = None,
    status: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    sort_desc: bool = False,
    load_input: bool = False,
    load_output: bool = False,
) -> List[WorkflowOutput]:
    manager = get_executor_manager()
    request_id = manager.new_request_id()
    body: p.ListQueuedWorkflowsBody = {
        "sort_desc": sort_desc,
        "load_input": load_input,
        "load_output": load_output,
    }
    if queue_name is not None:
        body["queue_name"] = queue_name
    if status is not None:
        body["status"] = status
    if limit is not None:
        body["limit"] = limit
    if offset is not None:
        body["offset"] = offset

    msg = p.ListQueuedWorkflowsRequest(
        type=p.MessageType.LIST_QUEUED_WORKFLOWS,
        request_id=request_id,
        body=body,
    )
    data = await _send_and_parse(manager, app_name, msg)
    if data.get("error_message"):
        raise HTTPException(status_code=502, detail=data["error_message"])
    return [WorkflowOutput(**w) for w in data.get("output", [])]


@router.get("/workflows/{workflow_id}/export")
async def export_workflow(
    app_name: str, workflow_id: str, export_children: bool = True
) -> dict:
    manager = get_executor_manager()
    request_id = manager.new_request_id()
    msg = p.ExportWorkflowRequest(
        type=p.MessageType.EXPORT_WORKFLOW,
        request_id=request_id,
        workflow_id=workflow_id,
        export_children=export_children,
    )
    data = await _send_and_parse(manager, app_name, msg)
    if data.get("error_message"):
        raise HTTPException(status_code=502, detail=data["error_message"])
    return {"serialized_workflow": data.get("serialized_workflow")}
