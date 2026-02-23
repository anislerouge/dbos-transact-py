from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class SuccessResponse(BaseModel):
    success: bool
    error_message: Optional[str] = None


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


class StartWorkflowParams(BaseModel):
    workflow_name: str
    args: List[Any] = []
    kwargs: Dict[str, Any] = {}


class StartWorkflowResponse(BaseModel):
    workflow_id: Optional[str] = None
    error_message: Optional[str] = None
