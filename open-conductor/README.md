# Open Conductor

Self-hosted, open-source replacement for [DBOS Conductor](https://cloud.dbos.dev). Manages DBOS workflows via a WebSocket proxy, exposes a REST API, and includes a React dashboard.

## Architecture

```
                                   ┌──────────────────────────────────┐
                                   │     Open Conductor Server        │
┌──────────────┐   WebSocket       │     (FastAPI + WebSocket)        │
│  DBOS App 1  │ <──────────────── │                                  │
│  DBOS App 2  │ ──────────────> │  ┌────────────────────────────┐  │
│  DBOS App N  │   DBOS Protocol   │  │  ExecutorManager           │  │
└──────┬───────┘                   │  │  - tracks connected apps   │  │
       │                           │  │  - round-robin routing     │  │
       │ SQL                       │  │  - request/response corr.  │  │
       │                           │  └────────────────────────────┘  │
       │                           │                                  │
       │                           │  REST API (/api/v1/*)            │
       │                           │      ^                           │
       │                           │      |                           │
       │                           │  React Dashboard (:5173)         │
       │                           └──────────────────────────────────┘
       v
┌─────────────────────────────────────────────────────┐
│  PostgreSQL — existing DBOS tables                   │
│  (dbos.workflow_status, dbos.operation_outputs, ...) │
└─────────────────────────────────────────────────────┘
```

**Key design**: Open Conductor is a **stateless proxy**. No new database tables. All workflow data lives in the DBOS app's existing PostgreSQL database. The server acts as a bridge between the dashboard/API and the DBOS executors connected via WebSocket.

## How it works

### Request flow

```
User clicks "Cancel" in Dashboard
    → POST /api/v1/apps/my-app/workflows/{id}/cancel
    → FastAPI builds CancelRequest(type=CANCEL, request_id=uuid)
    → ExecutorManager picks an executor (round-robin)
    → Sends JSON via WebSocket to the DBOS app
    → Waits for response (asyncio.Future, timeout 30s)
    → Returns SuccessResponse to the dashboard
```

### WebSocket handshake

1. DBOS app connects to `ws://conductor:8080/websocket/{app_name}/{conductor_key}`
2. Server validates the API key (if configured)
3. Server sends an `EXECUTOR_INFO` request
4. App responds with executor_id, hostname, language, version
5. Server registers the executor in the `ExecutorManager`
6. Enters a receive loop: every incoming message resolves a pending `asyncio.Future`

### Protocol

Open Conductor reuses the DBOS Conductor protocol (`dbos._conductor.protocol`) with 17+ message types:

| Message Type | Direction | Description |
|---|---|---|
| `EXECUTOR_INFO` | Server -> App | Request executor metadata |
| `LIST_WORKFLOWS` | Server -> App | List workflows with filters |
| `GET_WORKFLOW` | Server -> App | Get single workflow detail |
| `LIST_STEPS` | Server -> App | Get workflow step timeline |
| `CANCEL` | Server -> App | Cancel a running workflow |
| `RESUME` | Server -> App | Resume a cancelled workflow |
| `RESTART` | Server -> App | Restart a workflow |
| `FORK_WORKFLOW` | Server -> App | Fork a workflow from a step |
| `DELETE` | Server -> App | Delete a workflow |
| `LIST_QUEUED_WORKFLOWS` | Server -> App | List queued workflows |
| `EXPORT_WORKFLOW` | Server -> App | Serialize a workflow |
| `IMPORT_WORKFLOW` | Server -> App | Import a serialized workflow |
| `RECOVERY` | Server -> App | Trigger workflow recovery |
| `RETENTION` | Server -> App | Trigger garbage collection |
| `GET_METRICS` | Server -> App | Retrieve metrics |

**Open Conductor extensions** (prefix `oc_`):

| Message Type | Direction | Description |
|---|---|---|
| `oc_start_workflow` | Server -> App | Start a workflow by name with custom args/kwargs |

DBOS apps need the `executor_handler` plugin to support OC extensions (see [Executor Plugin](#executor-plugin)).

## Prerequisites

- Python 3.10+
- Node.js 18+ (for the dashboard)
- PostgreSQL (for the DBOS app)

## Installation

```bash
cd open_conductor

# Install everything (Python + Node)
make install-all

# Or separately:
make install       # Python deps via pdm (server + dev + db)
make install-web   # Node deps (dashboard)
```

## Quick start

### Start the server

```bash
make server
```

Server starts on `http://localhost:8080`. Swagger UI available at `http://localhost:8080/docs`.

### Start the dashboard

```bash
make dashboard
```

React dashboard starts on `http://localhost:5173` and proxies API calls to the server.

### Start server + dashboard together

```bash
make dev
```

### Run the full example

```bash
make example
```

This starts Open Conductor, then connects an example DBOS app with multiple workflow types. Verify:

```bash
# The app should appear
curl http://localhost:8080/api/v1/apps

# Connected executors
curl http://localhost:8080/api/v1/apps/example-app/executors

# List workflows
curl http://localhost:8080/api/v1/apps/example-app/workflows?sort_desc=true&limit=10

# Swagger
open http://localhost:8080/docs
```

> **Note:** The example requires a PostgreSQL database. By default it connects to
> `postgresql://postgres:admin@localhost:5432/example_db`. Edit `examples/connect_app.py`
> if your credentials differ.

## Connecting a DBOS app

Add `conductor_url` and `conductor_key` to your DBOS app config:

```python
from dbos import DBOS

DBOS(config={
    "name": "my-app",
    "database_url": "postgresql://...",
    "conductor_url": "ws://localhost:8080",
    "conductor_key": "dev-key",       # optional if api_keys is empty
})
```

The app automatically connects to the WebSocket at `/websocket/{app_name}/{conductor_key}` and appears in the API.

### Executor plugin

To support Open Conductor extensions (like starting workflows with custom params from the dashboard), install the OC handler in your DBOS app:

```python
from open_conductor.executor_handler import handle_oc_message
```

This allows the conductor to send `oc_start_workflow` messages to your app, which looks up the workflow by name in the DBOS registry and starts it with the provided args/kwargs. See `examples/connect_app.py` for a complete integration example.

## REST API

All routes are under `/api/v1`.

### Apps & Executors

| Method | Route | Description |
|---|---|---|
| `GET` | `/apps` | List connected apps with executor count |
| `GET` | `/apps/{name}/executors` | List connected executors for an app |

### Workflows (proxied via WebSocket)

| Method | Route | Description |
|---|---|---|
| `GET` | `/apps/{name}/workflows` | List workflows (filters: status, name, time range, limit/offset, load_input, load_output) |
| `GET` | `/apps/{name}/workflows/{id}` | Workflow detail (always loads input) |
| `GET` | `/apps/{name}/workflows/{id}/steps` | Step timeline (function_id, name, output, error, child_workflow_id, timestamps) |
| `POST` | `/apps/{name}/workflows/start` | Start a new workflow by name with args/kwargs (OC extension) |
| `POST` | `/apps/{name}/workflows/{id}/cancel` | Cancel a workflow |
| `POST` | `/apps/{name}/workflows/{id}/resume` | Resume a cancelled workflow |
| `POST` | `/apps/{name}/workflows/{id}/restart` | Restart a workflow |
| `POST` | `/apps/{name}/workflows/{id}/fork` | Fork from a specific step |
| `DELETE` | `/apps/{name}/workflows/{id}` | Delete a workflow |
| `GET` | `/apps/{name}/queued-workflows` | List queued workflows |
| `GET` | `/apps/{name}/workflows/{id}/export` | Export/serialize a workflow |
| `POST` | `/apps/{name}/workflows/import` | Import a serialized workflow |

### System

| Method | Route | Description |
|---|---|---|
| `POST` | `/apps/{name}/metrics` | Retrieve metrics |
| `POST` | `/apps/{name}/recovery` | Trigger workflow recovery |
| `POST` | `/apps/{name}/retention` | Trigger garbage collection |
| `GET` | `/health` | Server health + connected app count |

## Dashboard

The React dashboard provides:

- **Dashboard page** (`/`) — Health status, connected apps overview
- **Applications page** (`/apps`) — App list with expandable executor details (hostname, language, version)
- **Workflow list** (`/apps/:name/workflows`) — Filterable table with status badges, input/output preview, timestamps, duration. Actions: Cancel, Resume, Restart (with editable params modal)
- **Workflow detail** (`/apps/:name/workflows/:id`) — Info cards (name, status, started/ended, duration, queue, executor), input/output/error blocks, step timeline
- **Step timeline** — Distinguishes STEP (green badge) vs WORKFLOW (blue badge, clickable link to child workflow). Shows timestamps, duration, output, errors
- **Restart modal** — Pre-fills args/kwargs from the current workflow input (handles Python repr format: tuples, single quotes, trailing commas). Starts a new workflow via the `oc_start_workflow` extension
- **Queue view** (`/apps/:name/queues`) — Queued workflows table

### Input format handling

DBOS serializes workflow inputs as Python repr strings (e.g., `{'args': ('kafka',), 'kwargs': {}}`). The dashboard automatically converts this format to JSON for display and editing in the restart modal:
- Single quotes `'` → double quotes `"`
- Tuples `()` → arrays `[]`
- Trailing commas removed
- `True`/`False`/`None` → `true`/`false`/`null`

## Configuration

Environment variables (prefix `OPEN_CONDUCTOR_`):

| Variable | Default | Description |
|---|---|---|
| `OPEN_CONDUCTOR_HOST` | `0.0.0.0` | Listen address |
| `OPEN_CONDUCTOR_PORT` | `8080` | Server port |
| `OPEN_CONDUCTOR_API_KEYS` | `[]` | Allowed API keys (empty = no validation) |
| `OPEN_CONDUCTOR_WS_TIMEOUT` | `30.0` | WebSocket command timeout in seconds |
| `OPEN_CONDUCTOR_CORS_ORIGINS` | `["*"]` | Allowed CORS origins |
| `OPEN_CONDUCTOR_LOG_LEVEL` | `info` | Log level (debug, info, warning, error) |
| `OPEN_CONDUCTOR_SYSTEM_DATABASE_URL` | `null` | PostgreSQL URL for direct read-only queries (optional) |

## Core components

### ExecutorManager

Central registry that tracks all connected DBOS executors.

- **`_executors`**: `Dict[app_name, List[ExecutorInfo]]` — WebSocket connections per app
- **`_pending`**: `Dict[request_id, asyncio.Future]` — Request/response correlation
- **Round-robin**: Commands are distributed across executors of the same app
- **`send_command(app_name, message_json, request_id)`** — Sends a command and awaits the response (with configurable timeout)
- **`resolve_response(request_id, response_json)`** — Called from the WebSocket receive loop to resolve a pending Future

### WebSocket handler

Manages the lifecycle of an executor connection:
1. Validates API key
2. Accepts WebSocket
3. Sends `EXECUTOR_INFO` request to collect metadata
4. Registers executor in `ExecutorManager`
5. Enters receive loop (resolves Futures via `request_id` matching)
6. Unregisters executor on disconnect

### Protocol extensions

The `oc_start_workflow` message type is an Open Conductor extension. It allows the dashboard to start a workflow by name with custom arguments, without going through the standard DBOS protocol. The executor-side handler looks up the workflow in `DBOSRegistry.workflow_info_map` and calls `DBOS.start_workflow(func, *args, **kwargs)`.

## Tests

```bash
make test
```

16 tests covering:
- `test_executor_manager.py` — register/unregister, send_command, timeout, round-robin, no executor error
- `test_websocket.py` — handshake, API key validation, response routing
- `test_api.py` — REST endpoints with mock executor (health, apps, executors, cancel, workflows)

## Make commands

```
make help           Show all commands
make install        Install Python deps
make install-web    Install Node deps
make install-all    Install everything
make server         Start server (port 8080)
make dashboard      Start React dashboard (port 5173)
make dev            Start server + dashboard in parallel
make example        Start server + example app in parallel
make test           Run tests
make build-web      Production build of dashboard
make clean          Clean caches
make all            Install + test + dev
```

## Project structure

```
open_conductor/
├── Makefile
├── pyproject.toml
├── README.md
├── open_conductor/
│   ├── __init__.py
│   ├── __main__.py                 # Entry point: python -m open_conductor
│   ├── config.py                   # OpenConductorConfig (pydantic-settings)
│   ├── executor_handler.py         # OC extended message handler (for DBOS apps)
│   ├── executor_plugin.py          # Plugin installer (monkey-patches ConductorWebsocket)
│   ├── conductor/
│   │   ├── protocol.py             # Re-exports dbos._conductor.protocol + OC extensions
│   │   ├── executor_manager.py     # Tracks executors, routes commands, round-robin
│   │   └── websocket.py            # WebSocket handshake + receive loop
│   ├── server/
│   │   ├── app.py                  # FastAPI factory + WS routes + CORS + health
│   │   ├── deps.py                 # Dependency injection (config, executor_manager)
│   │   ├── models.py               # Pydantic DTOs (WorkflowOutput, StepOutput, etc.)
│   │   └── routes/
│   │       ├── apps.py             # GET /apps, GET /apps/{name}/executors
│   │       ├── workflows.py        # Workflow CRUD + start (proxy via WS)
│   │       └── system.py           # Metrics, recovery, retention
│   └── db/
│       ├── connection.py           # create_readonly_engine() (optional)
│       └── queries.py              # Direct SQL on dbos.workflow_status (optional)
├── web/                            # React dashboard (Vite + TypeScript)
│   ├── package.json
│   ├── vite.config.ts              # Dev proxy: /api -> localhost:8080
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx                  # Routes: /, /apps, /apps/:name/workflows, etc.
│       ├── api/client.ts            # Typed API client (fetch wrapper)
│       ├── components/
│       │   ├── Layout.tsx           # Sidebar navigation
│       │   ├── StatusBadge.tsx      # Color-coded workflow status
│       │   └── StepTimeline.tsx     # Step vs child workflow distinction
│       ├── pages/
│       │   ├── Dashboard.tsx        # Health + connected apps
│       │   ├── AppList.tsx          # Apps table with expandable executors
│       │   ├── WorkflowList.tsx     # Filterable workflow table + restart modal
│       │   ├── WorkflowDetail.tsx   # Workflow detail + steps + restart modal
│       │   └── QueueView.tsx        # Queued workflows
│       └── utils/
│           ├── parse.ts             # Python repr → JSON converter
│           └── time.ts              # formatEpoch, formatDuration
├── tests/
│   ├── conftest.py                  # Fixtures (config, manager, app, async client)
│   ├── test_executor_manager.py
│   ├── test_websocket.py
│   └── test_api.py
└── examples/
    └── connect_app.py               # Example DBOS app with 7 workflow types
```

## Example workflows

The `examples/connect_app.py` includes:

| Workflow | Description |
|---|---|
| `greet_workflow(name)` | Simple greeting, single step |
| `etl_pipeline(source)` | 3 steps: fetch_data → transform → load_result |
| `parallel_pipeline(sources)` | Starts multiple `etl_pipeline` children in parallel |
| `slow_job(duration)` | Long-running job with sleep |
| `approval_workflow()` | Creates a pending approval, waits for `approve()` |
| `approve(workflow_id, decision)` | Sends approval event to a waiting workflow |
| `orchestrator()` | Starts all workflow types as children |
