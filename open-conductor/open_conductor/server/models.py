from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel


class SuccessResponse(BaseModel):
    success: bool
    error_message: Optional[str] = None


class ExecutorOutput(BaseModel):
    executor_id: str
    app_name: str
    hostname: Optional[str] = None
    language: Optional[str] = None
    application_version: Optional[str] = None
    dbos_version: Optional[str] = None


class AppOutput(BaseModel):
    name: str
    executor_count: int


class WorkflowOutput(BaseModel):
    WorkflowUUID: str
    Status: Optional[str] = None
    WorkflowName: Optional[str] = None
    WorkflowClassName: Optional[str] = None
    WorkflowConfigName: Optional[str] = None
    AuthenticatedUser: Optional[str] = None
    AssumedRole: Optional[str] = None
    AuthenticatedRoles: Optional[str] = None
    Input: Optional[str] = None
    Output: Optional[str] = None
    Error: Optional[str] = None
    CreatedAt: Optional[str] = None
    UpdatedAt: Optional[str] = None
    QueueName: Optional[str] = None
    ApplicationVersion: Optional[str] = None
    ExecutorID: Optional[str] = None
    WorkflowTimeoutMS: Optional[str] = None
    WorkflowDeadlineEpochMS: Optional[str] = None
    DeduplicationID: Optional[str] = None
    Priority: Optional[str] = None
    QueuePartitionKey: Optional[str] = None
    ForkedFrom: Optional[str] = None
    ParentWorkflowID: Optional[str] = None
    DequeuedAt: Optional[str] = None


class StepOutput(BaseModel):
    function_id: int
    function_name: str
    output: Optional[str] = None
    error: Optional[str] = None
    child_workflow_id: Optional[str] = None
    started_at_epoch_ms: Optional[str] = None
    completed_at_epoch_ms: Optional[str] = None


class ListWorkflowsParams(BaseModel):
    workflow_name: Optional[Union[str, List[str]]] = None
    authenticated_user: Optional[Union[str, List[str]]] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: Optional[Union[str, List[str]]] = None
    application_version: Optional[Union[str, List[str]]] = None
    limit: Optional[int] = None
    offset: Optional[int] = None
    sort_desc: bool = False


class ForkWorkflowParams(BaseModel):
    start_step: int = 1
    application_version: Optional[str] = None
    new_workflow_id: Optional[str] = None


class RetentionParams(BaseModel):
    gc_cutoff_epoch_ms: Optional[int] = None
    gc_rows_threshold: Optional[int] = None
    timeout_cutoff_epoch_ms: Optional[int] = None


class RecoveryParams(BaseModel):
    executor_ids: List[str]


class MetricsParams(BaseModel):
    start_time: str
    end_time: str
    metric_class: str = "workflow_step_count"


class MetricOutput(BaseModel):
    metric_type: str
    metric_name: str
    value: int


class ImportWorkflowParams(BaseModel):
    serialized_workflow: str


class StartWorkflowParams(BaseModel):
    workflow_name: str
    args: List[Any] = []
    kwargs: Dict[str, Any] = {}


class StartWorkflowResponse(BaseModel):
    workflow_id: Optional[str] = None
    error_message: Optional[str] = None
