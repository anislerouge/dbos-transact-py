from functools import lru_cache
from typing import Optional

from open_conductor.conductor.executor_manager import ExecutorManager
from open_conductor.config import OpenConductorConfig

_config: Optional[OpenConductorConfig] = None
_executor_manager: Optional[ExecutorManager] = None


def init_dependencies(config: OpenConductorConfig) -> None:
    global _config, _executor_manager
    _config = config
    _executor_manager = ExecutorManager(ws_timeout=config.ws_timeout)


def get_config() -> OpenConductorConfig:
    assert _config is not None, "Dependencies not initialized"
    return _config


def get_executor_manager() -> ExecutorManager:
    assert _executor_manager is not None, "Dependencies not initialized"
    return _executor_manager
