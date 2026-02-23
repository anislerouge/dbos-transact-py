from typing import List

from fastapi import APIRouter, HTTPException
from open_conductor.server.deps import get_executor_manager
from open_conductor.server.models import AppOutput, ExecutorOutput

router = APIRouter(prefix="/api/v1", tags=["apps"])


@router.get("/apps", response_model=List[AppOutput])
async def list_apps() -> List[AppOutput]:
    manager = get_executor_manager()
    apps = manager.get_apps()
    return [
        AppOutput(name=name, executor_count=len(manager.get_executors(name)))
        for name in apps
    ]


@router.get("/apps/{app_name}/executors", response_model=List[ExecutorOutput])
async def list_executors(app_name: str) -> List[ExecutorOutput]:
    manager = get_executor_manager()
    executors = manager.get_executors(app_name)
    if not executors:
        raise HTTPException(
            status_code=404, detail=f"No executors found for app '{app_name}'"
        )
    return [
        ExecutorOutput(
            executor_id=e.executor_id,
            app_name=e.app_name,
            hostname=e.hostname,
            language=e.language,
            application_version=e.application_version,
            dbos_version=e.dbos_version,
        )
        for e in executors
    ]
