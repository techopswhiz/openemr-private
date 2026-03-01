# AI-generated: Claude Code (claude.ai/code) — config module
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # xAI / Grok
    xai_api_key: str = ""
    xai_model: str = "grok-3-mini-fast"
    xai_base_url: str = "https://api.x.ai/v1"

    # OpenEMR
    openemr_base_url: str = "http://localhost:8300"
    openemr_client_id: str = ""
    openemr_client_secret: str = ""
    openemr_username: str = "admin"
    openemr_password: str = "pass"

    # LangSmith
    langchain_tracing_v2: bool = True
    langchain_api_key: str = ""
    langchain_project: str = "openemr-agent"

    # App
    host: str = "0.0.0.0"
    port: int = 8080
    root_path: str = ""

    # Memory
    memory_db_path: str = "/data/sessions.db"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
# end AI-generated
