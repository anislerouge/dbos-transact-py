from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from open_conductor.conductor.websocket import handle_executor_connection
from open_conductor.config import OpenConductorConfig
from open_conductor.server.deps import (
    get_config,
    get_executor_manager,
    init_dependencies,
)
from open_conductor.server.routes import apps, system, workflows
from starlette.websockets import WebSocket


def create_app(config: OpenConductorConfig | None = None) -> FastAPI:
    if config is None:
        config = OpenConductorConfig()

    init_dependencies(config)

    app = FastAPI(
        title="Open Conductor",
        description="Self-hosted DBOS Conductor - manages DBOS workflows via WebSocket proxy",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # REST routes
    app.include_router(apps.router)
    app.include_router(workflows.router)
    app.include_router(system.router)

    # Health check
    @app.get("/health", tags=["system"])
    async def health() -> dict:
        manager = get_executor_manager()
        return {
            "status": "ok",
            "connected_apps": len(manager.get_apps()),
        }

    # WebSocket endpoint — matches the URL pattern DBOS apps use:
    #   conductor_url + /websocket/{app_name}/{conductor_key}
    @app.websocket("/websocket/{app_name}/{conductor_key}")
    async def websocket_endpoint(
        websocket: WebSocket, app_name: str, conductor_key: str
    ) -> None:
        manager = get_executor_manager()
        cfg = get_config()
        await handle_executor_connection(
            websocket, app_name, conductor_key, manager, cfg.api_keys
        )

    # Also support the /conductor/v1alpha1/websocket/ prefix (cloud compat)
    @app.websocket("/conductor/v1alpha1/websocket/{app_name}/{conductor_key}")
    async def websocket_endpoint_v1alpha1(
        websocket: WebSocket, app_name: str, conductor_key: str
    ) -> None:
        manager = get_executor_manager()
        cfg = get_config()
        await handle_executor_connection(
            websocket, app_name, conductor_key, manager, cfg.api_keys
        )

    return app


# Pour uvicorn avec reload (open_conductor.server.app:app)
app = create_app()
