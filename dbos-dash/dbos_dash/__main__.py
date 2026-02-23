import uvicorn

from .config import DashConfig

config = DashConfig()

uvicorn.run(
    "dbos_dash.app:app",
    host=config.host,
    port=config.port,
    log_level=config.log_level,
    reload=True,
)
