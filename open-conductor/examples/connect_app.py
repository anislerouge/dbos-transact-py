"""
Example: DBOS app that connects to Open Conductor.

Demonstrates workflows, steps, queues, child workflows, parallel execution,
send/recv communication, and sleep.

Usage:
    1. Start Open Conductor:
       cd open_conductor && python -m open_conductor

    2. Run this app:
       python examples/connect_app.py

    3. Check the dashboard:
       curl http://localhost:8080/api/v1/apps
       curl 'http://localhost:8080/api/v1/apps/example-app/workflows?load_input=true&load_output=true'
"""

import random
import time

# ── Patch conductor to support Open Conductor extended messages ──
from open_conductor.executor_handler import handle_oc_message

from dbos import DBOS, Queue
from dbos._conductor import conductor as _conductor
from dbos._conductor import protocol as _p

_original_handler = None


def _patch_conductor() -> None:
    """Monkey-patch ConductorWebsocket to handle OC messages."""
    original_run = _conductor.ConductorWebsocket.run

    def patched_run(self: _conductor.ConductorWebsocket) -> None:
        """Wrap run to intercept OC messages."""
        import websockets

        while not self.evt.is_set():
            try:
                with websockets.sync.client.connect(
                    self.url,
                    open_timeout=5,
                    close_timeout=5,
                    logger=self.dbos.logger,
                    max_size=None,
                ) as websocket:
                    self.websocket = websocket
                    if _conductor.use_keepalive and self.keepalive_thread is None:
                        import threading

                        self.keepalive_thread = threading.Thread(
                            target=self.keepalive,
                            daemon=True,
                        )
                        self.keepalive_thread.start()
                    while not self.evt.is_set():
                        message = websocket.recv()
                        if not isinstance(message, str):
                            continue
                        # Try OC handler first
                        oc_response = handle_oc_message(self.dbos, message)
                        if oc_response is not None:
                            websocket.send(oc_response)
                            continue
                        # Fall back to standard DBOS handler
                        base_message = _p.BaseMessage.from_json(message)
                        msg_type = base_message.type
                        error_message = None
                        if msg_type == _p.MessageType.EXECUTOR_INFO:
                            import socket as _socket

                            from dbos._utils import GlobalParams

                            info_response = _p.ExecutorInfoResponse(
                                type=_p.MessageType.EXECUTOR_INFO,
                                request_id=base_message.request_id,
                                executor_id=GlobalParams.executor_id,
                                application_version=GlobalParams.app_version,
                                hostname=_socket.gethostname(),
                                language="python",
                                dbos_version=GlobalParams.dbos_version,
                            )
                            websocket.send(info_response.to_json())
                            self.dbos.logger.info(
                                "Connected to DBOS conductor (OC-patched)"
                            )
                        else:
                            # Delegate all other messages to original logic
                            # by re-dispatching through the original handler code
                            _handle_standard_message(
                                self, websocket, message, base_message, msg_type
                            )
            except websockets.ConnectionClosedOK:
                if self.evt.is_set():
                    break
                time.sleep(1)
            except websockets.ConnectionClosed:
                time.sleep(1)
            except websockets.InvalidStatus as e:
                json_data = e.response.body.decode("utf-8")
                self.dbos.logger.error(
                    f"Failed to connect to conductor: {e}. {json_data}"
                )
                time.sleep(1)
            except Exception as e:
                self.dbos.logger.warning(f"Unexpected conductor error: {e}")
                time.sleep(1)
        if self.keepalive_thread is not None:
            if self.pong_event is not None:
                self.pong_event.set()
            self.keepalive_thread.join()

    _conductor.ConductorWebsocket.run = patched_run


def _handle_standard_message(conductor_ws, websocket, message, base_message, msg_type):
    """Handle all standard DBOS protocol messages."""
    import base64
    import gzip
    import pickle
    import traceback

    from dbos._context import SetWorkflowID
    from dbos._utils import generate_uuid
    from dbos._workflow_commands import (
        delete_workflow,
        garbage_collect,
        get_workflow,
        global_timeout,
    )

    dbos = conductor_ws.dbos
    error_message = None

    if msg_type == _p.MessageType.RECOVERY:
        msg = _p.RecoveryRequest.from_json(message)
        success = True
        try:
            dbos._recover_pending_workflows(msg.executor_ids)
        except Exception:
            error_message = traceback.format_exc()
            success = False
        websocket.send(
            _p.RecoveryResponse(
                type=_p.MessageType.RECOVERY,
                request_id=base_message.request_id,
                success=success,
                error_message=error_message,
            ).to_json()
        )
    elif msg_type == _p.MessageType.CANCEL:
        msg = _p.CancelRequest.from_json(message)
        success = True
        try:
            dbos.cancel_workflow(msg.workflow_id)
        except Exception:
            error_message = traceback.format_exc()
            success = False
        websocket.send(
            _p.CancelResponse(
                type=_p.MessageType.CANCEL,
                request_id=base_message.request_id,
                success=success,
                error_message=error_message,
            ).to_json()
        )
    elif msg_type == _p.MessageType.DELETE:
        msg = _p.DeleteRequest.from_json(message)
        success = True
        try:
            delete_workflow(dbos, msg.workflow_id, delete_children=msg.delete_children)
        except Exception:
            error_message = traceback.format_exc()
            success = False
        websocket.send(
            _p.DeleteResponse(
                type=_p.MessageType.DELETE,
                request_id=base_message.request_id,
                success=success,
                error_message=error_message,
            ).to_json()
        )
    elif msg_type == _p.MessageType.RESUME:
        msg = _p.ResumeRequest.from_json(message)
        success = True
        try:
            dbos.resume_workflow(msg.workflow_id)
        except Exception:
            error_message = traceback.format_exc()
            success = False
        websocket.send(
            _p.ResumeResponse(
                type=_p.MessageType.RESUME,
                request_id=base_message.request_id,
                success=success,
                error_message=error_message,
            ).to_json()
        )
    elif msg_type == _p.MessageType.RESTART:
        msg = _p.RestartRequest.from_json(message)
        success = True
        try:
            dbos.fork_workflow(msg.workflow_id, 1)
        except Exception:
            error_message = traceback.format_exc()
            success = False
        websocket.send(
            _p.RestartResponse(
                type=_p.MessageType.RESTART,
                request_id=base_message.request_id,
                success=success,
                error_message=error_message,
            ).to_json()
        )
    elif msg_type == _p.MessageType.FORK_WORKFLOW:
        msg = _p.ForkWorkflowRequest.from_json(message)
        new_wf_id = msg.body.get("new_workflow_id") or generate_uuid()
        try:
            with SetWorkflowID(new_wf_id):
                h = dbos.fork_workflow(
                    msg.body["workflow_id"],
                    msg.body["start_step"],
                    application_version=msg.body.get("application_version"),
                )
            new_wf_id = h.workflow_id
        except Exception:
            error_message = traceback.format_exc()
            new_wf_id = None
        websocket.send(
            _p.ForkWorkflowResponse(
                type=_p.MessageType.FORK_WORKFLOW,
                request_id=base_message.request_id,
                new_workflow_id=new_wf_id,
                error_message=error_message,
            ).to_json()
        )
    elif msg_type == _p.MessageType.LIST_WORKFLOWS:
        msg = _p.ListWorkflowsRequest.from_json(message)
        body = msg.body
        infos = []
        try:
            infos = dbos._sys_db.list_workflows(
                workflow_ids=body.get("workflow_uuids"),
                user=body.get("authenticated_user"),
                start_time=body.get("start_time"),
                end_time=body.get("end_time"),
                status=body.get("status"),
                app_version=body.get("application_version"),
                forked_from=body.get("forked_from"),
                parent_workflow_id=body.get("parent_workflow_id"),
                name=body.get("workflow_name"),
                queue_name=body.get("queue_name"),
                limit=body.get("limit"),
                offset=body.get("offset"),
                sort_desc=body.get("sort_desc", False),
                workflow_id_prefix=body.get("workflow_id_prefix"),
                load_input=body.get("load_input", False),
                load_output=body.get("load_output", False),
                executor_id=body.get("executor_id"),
                queues_only=body.get("queues_only", False),
            )
        except Exception:
            error_message = traceback.format_exc()
        websocket.send(
            _p.ListWorkflowsResponse(
                type=_p.MessageType.LIST_WORKFLOWS,
                request_id=base_message.request_id,
                output=[_p.WorkflowsOutput.from_workflow_information(i) for i in infos],
                error_message=error_message,
            ).to_json()
        )
    elif msg_type == _p.MessageType.LIST_QUEUED_WORKFLOWS:
        msg = _p.ListQueuedWorkflowsRequest.from_json(message)
        body = msg.body
        infos = []
        try:
            infos = dbos._sys_db.list_workflows(
                workflow_ids=body.get("workflow_uuids"),
                user=body.get("authenticated_user"),
                start_time=body.get("start_time"),
                end_time=body.get("end_time"),
                status=body.get("status"),
                app_version=body.get("application_version"),
                forked_from=body.get("forked_from"),
                parent_workflow_id=body.get("parent_workflow_id"),
                name=body.get("workflow_name"),
                queue_name=body.get("queue_name"),
                limit=body.get("limit"),
                offset=body.get("offset"),
                sort_desc=body.get("sort_desc", False),
                workflow_id_prefix=body.get("workflow_id_prefix"),
                load_input=body.get("load_input", False),
                load_output=body.get("load_output", False),
                executor_id=body.get("executor_id"),
                queues_only=True,
            )
        except Exception:
            error_message = traceback.format_exc()
        websocket.send(
            _p.ListQueuedWorkflowsResponse(
                type=_p.MessageType.LIST_QUEUED_WORKFLOWS,
                request_id=base_message.request_id,
                output=[_p.WorkflowsOutput.from_workflow_information(i) for i in infos],
                error_message=error_message,
            ).to_json()
        )
    elif msg_type == _p.MessageType.GET_WORKFLOW:
        msg = _p.GetWorkflowRequest.from_json(message)
        info = None
        try:
            info = get_workflow(dbos._sys_db, msg.workflow_id)
        except Exception:
            error_message = traceback.format_exc()
        websocket.send(
            _p.GetWorkflowResponse(
                type=_p.MessageType.GET_WORKFLOW,
                request_id=base_message.request_id,
                output=(
                    _p.WorkflowsOutput.from_workflow_information(info) if info else None
                ),
                error_message=error_message,
            ).to_json()
        )
    elif msg_type == _p.MessageType.EXIST_PENDING_WORKFLOWS:
        msg = _p.ExistPendingWorkflowsRequest.from_json(message)
        pending = []
        try:
            pending = dbos._sys_db.get_pending_workflows(
                msg.executor_id, msg.application_version
            )
        except Exception:
            error_message = traceback.format_exc()
        websocket.send(
            _p.ExistPendingWorkflowsResponse(
                type=_p.MessageType.EXIST_PENDING_WORKFLOWS,
                request_id=base_message.request_id,
                exist=len(pending) > 0,
                error_message=error_message,
            ).to_json()
        )
    elif msg_type == _p.MessageType.LIST_STEPS:
        msg = _p.ListStepsRequest.from_json(message)
        step_info = None
        try:
            step_info = dbos._sys_db.list_workflow_steps(msg.workflow_id)
        except Exception:
            error_message = traceback.format_exc()
        websocket.send(
            _p.ListStepsResponse(
                type=_p.MessageType.LIST_STEPS,
                request_id=base_message.request_id,
                output=(
                    [_p.WorkflowSteps.from_step_info(i) for i in step_info]
                    if step_info
                    else None
                ),
                error_message=error_message,
            ).to_json()
        )
    elif msg_type == _p.MessageType.RETENTION:
        msg = _p.RetentionRequest.from_json(message)
        success = True
        try:
            garbage_collect(
                dbos,
                cutoff_epoch_timestamp_ms=msg.body["gc_cutoff_epoch_ms"],
                rows_threshold=msg.body["gc_rows_threshold"],
            )
            if msg.body["timeout_cutoff_epoch_ms"] is not None:
                global_timeout(dbos, msg.body["timeout_cutoff_epoch_ms"])
        except Exception:
            error_message = traceback.format_exc()
            success = False
        websocket.send(
            _p.RetentionResponse(
                type=_p.MessageType.RETENTION,
                request_id=base_message.request_id,
                success=success,
                error_message=error_message,
            ).to_json()
        )
    elif msg_type == _p.MessageType.GET_METRICS:
        msg = _p.GetMetricsRequest.from_json(message)
        metrics_data = []
        if msg.metric_class == "workflow_step_count":
            try:
                sys_metrics = dbos._sys_db.get_metrics(msg.start_time, msg.end_time)
                metrics_data = [
                    _p.MetricData(
                        metric_type=m["metric_type"],
                        metric_name=m["metric_name"],
                        value=m["value"],
                    )
                    for m in sys_metrics
                ]
            except Exception:
                error_message = traceback.format_exc()
        else:
            error_message = f"Unexpected metric class: {msg.metric_class}"
        websocket.send(
            _p.GetMetricsResponse(
                type=_p.MessageType.GET_METRICS,
                request_id=base_message.request_id,
                metrics=metrics_data,
                error_message=error_message,
            ).to_json()
        )
    elif msg_type == _p.MessageType.EXPORT_WORKFLOW:
        msg = _p.ExportWorkflowRequest.from_json(message)
        serialized = None
        try:
            exported = dbos._sys_db.export_workflow(
                msg.workflow_id, export_children=msg.export_children
            )
            serialized = base64.b64encode(gzip.compress(pickle.dumps(exported))).decode(
                "utf-8"
            )
        except Exception:
            error_message = traceback.format_exc()
        websocket.send(
            _p.ExportWorkflowResponse(
                type=_p.MessageType.EXPORT_WORKFLOW,
                request_id=base_message.request_id,
                serialized_workflow=serialized,
                error_message=error_message,
            ).to_json()
        )
    elif msg_type == _p.MessageType.IMPORT_WORKFLOW:
        msg = _p.ImportWorkflowRequest.from_json(message)
        success = True
        try:
            workflow = pickle.loads(
                gzip.decompress(base64.b64decode(msg.serialized_workflow))
            )
            dbos._sys_db.import_workflow(workflow)
        except Exception:
            error_message = traceback.format_exc()
            success = False
        websocket.send(
            _p.ImportWorkflowResponse(
                type=_p.MessageType.IMPORT_WORKFLOW,
                request_id=base_message.request_id,
                success=success,
                error_message=error_message,
            ).to_json()
        )
    elif msg_type == _p.MessageType.ALERT:
        msg = _p.AlertRequest.from_json(message)
        success = True
        try:
            if dbos._alert_handler is not None:
                dbos._alert_handler(msg.name, msg.message, msg.metadata)
        except Exception:
            error_message = traceback.format_exc()
            success = False
        websocket.send(
            _p.AlertResponse(
                type=_p.MessageType.ALERT,
                request_id=base_message.request_id,
                success=success,
                error_message=error_message,
            ).to_json()
        )
    else:
        websocket.send(
            _p.BaseResponse(
                request_id=base_message.request_id,
                type=msg_type,
                error_message="Unknown message type",
            ).to_json()
        )


_patch_conductor()

DBOS(
    config={
        "name": "example-app",
        "database_url": "postgresql://postgres:admin@localhost:5432/example_db",
        "conductor_url": "ws://localhost:8080",
        "conductor_key": "dev-key",
    }
)

# ── Queues ────────────────────────────────────────────────────

fast_queue = Queue("fast-queue", concurrency=3)
slow_queue = Queue("slow-queue", concurrency=1)

# ── Steps ─────────────────────────────────────────────────────


@DBOS.step()
def fetch_data(source: str) -> dict:
    """Simulate fetching data from an external source."""
    DBOS.logger.info(f"Fetching data from {source}...")
    time.sleep(0.2)
    return {"source": source, "rows": random.randint(10, 500)}


@DBOS.step()
def transform(data: dict) -> dict:
    """Simulate data transformation."""
    DBOS.logger.info(f"Transforming {data['rows']} rows from {data['source']}")
    time.sleep(0.1)
    return {**data, "transformed": True, "output_rows": data["rows"] * 2}


@DBOS.step()
def load_result(data: dict) -> str:
    """Simulate loading results to a destination."""
    DBOS.logger.info(f"Loading {data['output_rows']} rows")
    time.sleep(0.1)
    return f"Loaded {data['output_rows']} rows from {data['source']}"


@DBOS.step()
def send_notification(message: str) -> str:
    """Simulate sending a notification."""
    DBOS.logger.info(f"Notification: {message}")
    time.sleep(0.05)
    return f"Notified: {message}"


# ── Simple workflow ───────────────────────────────────────────


@DBOS.workflow()
def greet_workflow(name: str) -> str:
    """Simple single-step workflow."""
    return send_notification(f"Hello, {name}!")


# ── ETL pipeline (multi-step) ────────────────────────────────


@DBOS.workflow()
def etl_pipeline(source: str) -> str:
    """Multi-step ETL workflow: fetch -> transform -> load."""
    raw = fetch_data(source)
    transformed = transform(raw)
    result = load_result(transformed)
    send_notification(result)
    return result


# ── Parallel fan-out / fan-in ─────────────────────────────────


@DBOS.workflow()
def parallel_pipeline(sources: list) -> dict:
    """Fan-out: launch child ETL workflows in parallel via queue, then aggregate."""
    handles = []
    for source in sources:
        h = fast_queue.enqueue(etl_pipeline, source)
        handles.append(h)

    # Fan-in: collect all results
    results = []
    for h in handles:
        results.append(h.get_result())

    summary = f"Processed {len(results)} sources"
    send_notification(summary)
    return {"summary": summary, "results": results}


# ── Slow queue workflow ───────────────────────────────────────


@DBOS.workflow()
def slow_job(job_id: int) -> str:
    """A slow job that runs one at a time via slow-queue."""
    DBOS.sleep(1)
    result = fetch_data(f"slow-source-{job_id}")
    return f"Slow job {job_id} done: {result['rows']} rows"


# ── Workflow with send/recv communication ─────────────────────


@DBOS.workflow()
def approval_workflow(request_name: str) -> str:
    """Workflow that waits for external approval via send/recv."""
    send_notification(f"Approval requested for: {request_name}")

    # Wait for approval (timeout 10s)
    decision = DBOS.recv("approval", timeout_seconds=10)

    if decision == "approved":
        return f"{request_name}: APPROVED"
    else:
        return f"{request_name}: REJECTED (got: {decision})"


@DBOS.workflow()
def approve(target_workflow_id: str, decision: str) -> str:
    """Send an approval decision to a waiting workflow."""
    DBOS.send(target_workflow_id, decision, "approval")
    return f"Sent '{decision}' to {target_workflow_id}"


# ── Orchestrator: workflow that calls other workflows ─────────


@DBOS.workflow()
def orchestrator(project: str) -> dict:
    """Top-level workflow that coordinates multiple child workflows."""
    # Step 1: greet the team
    greet_handle = DBOS.start_workflow(greet_workflow, f"team {project}")

    # Step 2: run 3 ETL pipelines as children
    etl_handles = []
    for source in [f"{project}-db", f"{project}-api", f"{project}-files"]:
        h = DBOS.start_workflow(etl_pipeline, source)
        etl_handles.append(h)

    # Step 3: while ETLs run, enqueue slow jobs
    slow_handles = []
    for i in range(2):
        h = slow_queue.enqueue(slow_job, 100 + i)
        slow_handles.append(h)

    # Step 4: request approval and auto-approve
    approval_h = DBOS.start_workflow(approval_workflow, f"{project}-release")
    DBOS.start_workflow(approve, approval_h.workflow_id, "approved")

    # Collect all results
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


# ── Main ──────────────────────────────────────────────────────

if __name__ == "__main__":
    DBOS.launch()
    print("App connected to Open Conductor.\n")

    # 1. Simple workflows
    print("=== Simple workflows ===")
    for name in ["Alice", "Bob", "Charlie"]:
        h = DBOS.start_workflow(greet_workflow, name)
        print(f"  {h.workflow_id}: {h.get_result()}")

    # 2. Multi-step ETL pipeline
    print("\n=== ETL pipelines ===")
    for src in ["postgres-db", "s3-bucket", "api-endpoint"]:
        h = DBOS.start_workflow(etl_pipeline, src)
        print(f"  {h.workflow_id}: {h.get_result()}")

    # 3. Parallel fan-out/fan-in
    print("\n=== Parallel pipeline ===")
    h = DBOS.start_workflow(
        parallel_pipeline, ["redis", "kafka", "mongodb", "elasticsearch"]
    )
    result = h.get_result()
    print(f"  {h.workflow_id}: {result['summary']}")

    # 4. Slow queue (concurrency=1)
    print("\n=== Slow queue (3 jobs, concurrency=1) ===")
    slow_handles = []
    for i in range(3):
        sh = slow_queue.enqueue(slow_job, i)
        slow_handles.append(sh)
        print(f"  Enqueued slow job {i}: {sh.workflow_id}")

    # 5. Approval workflow with send/recv
    print("\n=== Approval workflow ===")
    approval_handle = DBOS.start_workflow(approval_workflow, "deploy-v2.0")
    print(f"  Waiting for approval: {approval_handle.workflow_id}")

    # Auto-approve after a short delay
    approve_h = DBOS.start_workflow(approve, approval_handle.workflow_id, "approved")
    print(f"  Approver: {approve_h.workflow_id}: {approve_h.get_result()}")
    print(f"  Approval result: {approval_handle.get_result()}")

    # Wait for slow jobs to complete
    print("\n=== Slow queue results ===")
    for sh in slow_handles:
        print(f"  {sh.workflow_id}: {sh.get_result()}")

    # 6. Orchestrator: one workflow that calls many others
    print("\n=== Orchestrator ===")
    orch_h = DBOS.start_workflow(orchestrator, "phoenix")
    orch_result = orch_h.get_result()
    print(f"  {orch_h.workflow_id}: {orch_result['summary']}")
    print(f"    ETLs:      {len(orch_result['etl'])}")
    print(f"    Slow jobs:  {len(orch_result['slow_jobs'])}")
    print(f"    Approval:   {orch_result['approval']}")

    print(
        f"\nAll done! Check http://localhost:8080/api/v1/apps/example-app/workflows?load_input=true&load_output=true"
    )
    print("Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        DBOS.destroy()
