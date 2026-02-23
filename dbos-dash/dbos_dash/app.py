from pathlib import Path

from dbos_dash.config import DashConfig
from dbos_dash.routes.health import router as health_router
from dbos_dash.routes.health import set_config as set_health_config
from dbos_dash.routes.workflows import router as workflow_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from dbos import DBOS
from dbos._fastapi import setup_fastapi_middleware


def create_app(config: DashConfig | None = None) -> FastAPI:
    if config is None:
        config = DashConfig()

    app = FastAPI(title="DBOS Dash")

    dbos = DBOS(
        config={
            "name": config.app_name,
            "database_url": config.database_url,
        }
    )
    setup_fastapi_middleware(app, dbos)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register example workflows
    import dbos_dash.workflows as _workflows  # noqa: F401

    del _workflows

    set_health_config(config)
    app.include_router(health_router)
    app.include_router(workflow_router, prefix="/api/v1")

    # Serve frontend static files if built
    if config.serve_frontend:
        dist_dir = Path(__file__).parent.parent / "web" / "dist"
        if dist_dir.is_dir():
            app.mount(
                "/", StaticFiles(directory=str(dist_dir), html=True), name="static"
            )

    return app


app = create_app()
