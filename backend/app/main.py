from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import audit, auth, documents, models, projects
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


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}
