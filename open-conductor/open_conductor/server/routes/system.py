import json
from typing import List

from fastapi import APIRouter, HTTPException
from open_conductor.conductor import protocol as p
from open_conductor.conductor.executor_manager import ExecutorManager
from open_conductor.server.deps import get_executor_manager
from open_conductor.server.models import (
    MetricOutput,
    MetricsParams,
    RecoveryParams,
    RetentionParams,
    SuccessResponse,
)

router = APIRouter(prefix="/api/v1/apps/{app_name}", tags=["system"])


async def _send_and_parse(
    manager: ExecutorManager, app_name: str, message: p.BaseMessage
) -> dict:
    try:
        raw = await manager.send_command(
            app_name, message.to_json(), message.request_id
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except TimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    return json.loads(raw)


@router.post("/metrics", response_model=List[MetricOutput])
async def get_metrics(app_name: str, params: MetricsParams) -> List[MetricOutput]:
    manager = get_executor_manager()
    request_id = manager.new_request_id()
    msg = p.GetMetricsRequest(
        type=p.MessageType.GET_METRICS,
        request_id=request_id,
        start_time=params.start_time,
        end_time=params.end_time,
        metric_class=params.metric_class,
    )
    data = await _send_and_parse(manager, app_name, msg)
    if data.get("error_message"):
        raise HTTPException(status_code=502, detail=data["error_message"])
    return [MetricOutput(**m) for m in data.get("metrics", [])]


@router.post("/recovery", response_model=SuccessResponse)
async def trigger_recovery(app_name: str, params: RecoveryParams) -> SuccessResponse:
    manager = get_executor_manager()
    request_id = manager.new_request_id()
    msg = p.RecoveryRequest(
        type=p.MessageType.RECOVERY,
        request_id=request_id,
        executor_ids=params.executor_ids,
    )
    data = await _send_and_parse(manager, app_name, msg)
    return SuccessResponse(
        success=data.get("success", False), error_message=data.get("error_message")
    )


@router.post("/retention", response_model=SuccessResponse)
async def trigger_retention(app_name: str, params: RetentionParams) -> SuccessResponse:
    manager = get_executor_manager()
    request_id = manager.new_request_id()
    body: p.RetentionBody = {
        "gc_cutoff_epoch_ms": params.gc_cutoff_epoch_ms,
        "gc_rows_threshold": params.gc_rows_threshold,
        "timeout_cutoff_epoch_ms": params.timeout_cutoff_epoch_ms,
    }
    msg = p.RetentionRequest(
        type=p.MessageType.RETENTION,
        request_id=request_id,
        body=body,
    )
    data = await _send_and_parse(manager, app_name, msg)
    return SuccessResponse(
        success=data.get("success", False), error_message=data.get("error_message")
    )
