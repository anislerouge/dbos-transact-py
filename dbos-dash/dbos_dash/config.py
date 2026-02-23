from pydantic_settings import BaseSettings


class DashConfig(BaseSettings):
    model_config = {"env_prefix": "DBOS_DASH_"}

    app_name: str = "dbos-dash"
    database_url: str = "postgresql://postgres:admin@localhost:5432/dbos_dash_db"
    host: str = "0.0.0.0"
    port: int = 8080
    cors_origins: list[str] = ["*"]
    log_level: str = "info"
    serve_frontend: bool = True
