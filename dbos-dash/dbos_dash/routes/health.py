from dbos_dash.config import DashConfig
from fastapi import APIRouter

router = APIRouter()

_config: DashConfig | None = None


def set_config(config: DashConfig) -> None:
    global _config
    _config = config


@router.get("/health")
async def health():
    return {"status": "ok", "app_name": _config.app_name if _config else "dbos-dash"}
