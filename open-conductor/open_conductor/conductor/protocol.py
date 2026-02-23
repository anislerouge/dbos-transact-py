# Re-export all protocol types from the DBOS conductor protocol.
# This avoids duplication and stays in sync with the DBOS SDK.
import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from dbos._conductor.protocol import (  # noqa: F401
    AlertRequest,
    AlertResponse,
    BaseMessage,
    BaseResponse,
    CancelRequest,
    CancelResponse,
    DeleteRequest,
    DeleteResponse,
    ExecutorInfoRequest,
    ExecutorInfoResponse,
    ExistPendingWorkflowsRequest,
    ExistPendingWorkflowsResponse,
    ExportWorkflowRequest,
    ExportWorkflowResponse,
    ForkWorkflowBody,
    ForkWorkflowRequest,
    ForkWorkflowResponse,
    GetMetricsRequest,
    GetMetricsResponse,
    GetWorkflowRequest,
    GetWorkflowResponse,
    ImportWorkflowRequest,
    ImportWorkflowResponse,
    ListQueuedWorkflowsBody,
    ListQueuedWorkflowsRequest,
    ListQueuedWorkflowsResponse,
    ListStepsRequest,
    ListStepsResponse,
    ListWorkflowsBody,
    ListWorkflowsRequest,
    ListWorkflowsResponse,
    MessageType,
    MetricData,
    RecoveryRequest,
    RecoveryResponse,
    RestartRequest,
    RestartResponse,
    ResumeRequest,
    ResumeResponse,
    RetentionBody,
    RetentionRequest,
    RetentionResponse,
    WorkflowsOutput,
    WorkflowSteps,
)

# ── Open Conductor extensions ─────────────────────────────────
# These message types extend the DBOS protocol for Open Conductor features.
# DBOS executors need the open_conductor_handler plugin to support them.


class OpenConductorMessageType:
    START_WORKFLOW = "oc_start_workflow"


@dataclass
class StartWorkflowRequest(BaseMessage):
    """Request to start a workflow by name with given arguments."""

    workflow_name: str
    args: List[Any]
    kwargs: Dict[str, Any]


@dataclass
class StartWorkflowResponse(BaseMessage):
    workflow_id: Optional[str] = None
    error_message: Optional[str] = None
