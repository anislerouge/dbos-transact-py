from dbos import DBOS, Queue

from .etl import etl_pipeline, fetch_data
from .greeting import greet_workflow, send_notification

slow_queue = Queue("slow-queue", concurrency=1)


@DBOS.workflow()
def slow_job(job_id: int) -> str:
    DBOS.sleep(1)
    result = fetch_data(f"slow-source-{job_id}")
    return f"Slow job {job_id} done: {result['rows']} rows"


@DBOS.workflow()
def approval_workflow(request_name: str) -> str:
    send_notification(f"Approval requested for: {request_name}")
    decision = DBOS.recv("approval", timeout_seconds=10)
    if decision == "approved":
        return f"{request_name}: APPROVED"
    else:
        return f"{request_name}: REJECTED (got: {decision})"


@DBOS.workflow()
def approve(target_workflow_id: str, decision: str) -> str:
    DBOS.send(target_workflow_id, decision, "approval")
    return f"Sent '{decision}' to {target_workflow_id}"


@DBOS.workflow()
def orchestrator(project: str) -> dict:
    greet_handle = DBOS.start_workflow(greet_workflow, f"team {project}")

    etl_handles = []
    for source in [f"{project}-db", f"{project}-api", f"{project}-files"]:
        h = DBOS.start_workflow(etl_pipeline, source)
        etl_handles.append(h)

    slow_handles = []
    for i in range(2):
        h = slow_queue.enqueue(slow_job, 100 + i)
        slow_handles.append(h)

    approval_h = DBOS.start_workflow(approval_workflow, f"{project}-release")
    DBOS.start_workflow(approve, approval_h.workflow_id, "approved")

    greet_result = greet_handle.get_result()
    etl_results = [h.get_result() for h in etl_handles]
    slow_results = [h.get_result() for h in slow_handles]
    approval_result = approval_h.get_result()

    summary = send_notification(
        f"Orchestrator {project} complete: {len(etl_results)} ETLs, {len(slow_results)} jobs"
    )

    return {
        "project": project,
        "greet": greet_result,
        "etl": etl_results,
        "slow_jobs": slow_results,
        "approval": approval_result,
        "summary": summary,
    }
