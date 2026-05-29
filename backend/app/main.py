from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError

from app.api import audit, auth, documents, models, openmbee, projects, versioning
from app.core.config import get_settings
from app.core.database import init_db


settings = get_settings()
settings.upload_path.mkdir(parents=True, exist_ok=True)
settings.generated_path.mkdir(parents=True, exist_ok=True)
init_db()

app = FastAPI(
    title="SysMLDocGen API",
    description="基于 SysML 模型的文档自动生成系统后端接口",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(models.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(versioning.router, prefix="/api")
app.include_router(openmbee.router, prefix="/api")


@app.exception_handler(OperationalError)
def operational_error_handler(_, exc: OperationalError):
    if _is_mysql_lock_error(exc):
        return JSONResponse(
            status_code=409,
            content={"detail": "数据库记录正在被其他请求占用，请稍后重试；如果持续出现，请重启后端或释放 MySQL 持锁会话"},
        )
    return JSONResponse(status_code=500, content={"detail": "数据库操作失败"})


def _is_mysql_lock_error(exc: OperationalError) -> bool:
    code = getattr(getattr(exc, "orig", None), "args", [None])[0]
    return code in {1205, 1213}


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}
