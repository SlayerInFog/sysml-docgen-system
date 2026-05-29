from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "SysMLDocGen"
    database_url: str = "mysql+pymysql://root:mysql@127.0.0.1:3306/sysml_docgen?charset=utf8mb4"
    secret_key: str = "sysml-docgen-dev-secret"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    upload_dir: str = "app/uploads"
    generated_dir: str = "app/generated"
    openmbee_mms_url: str | None = None
    openmbee_mms_token: str | None = None
    openmbee_doc_convert_url: str | None = None
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def upload_path(self) -> Path:
        return Path(self.upload_dir)

    @property
    def generated_path(self) -> Path:
        return Path(self.generated_dir)


@lru_cache
def get_settings() -> Settings:
    return Settings()
