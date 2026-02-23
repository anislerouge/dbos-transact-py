from typing import List, Optional

from pydantic_settings import BaseSettings


class OpenConductorConfig(BaseSettings):
    model_config = {"env_prefix": "OPEN_CONDUCTOR_"}

    host: str = "0.0.0.0"
    port: int = 8080
    api_keys: List[str] = []
    system_database_url: Optional[str] = None
    ws_timeout: float = 30.0
    cors_origins: List[str] = ["*"]
    log_level: str = "info"
