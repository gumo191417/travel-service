from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.clients.database import (
    close_db_engine,
    init_db_engine,
)
from app.clients.http_client import (
    close_http_client,
    init_http_client,
)
from app.web.chat_router import chat_router
from app.web.dependencies import init_dialogue_engine
from app.web.handoff_router import handoff_router

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：初始化 HTTP Client、共享引擎、数据库 Engine
    init_http_client()
    init_dialogue_engine()
    init_db_engine()

    yield  # 服务运行阶段

    # 关闭：先释放数据库，再释放 HTTP Client
    await close_db_engine()
    await close_http_client()


app = FastAPI(
    title="旅游智能客服系统",
    description="酒店、景点、交通票务、订单与退款的智能客服",
    lifespan=lifespan,
)
app.include_router(chat_router)
app.include_router(handoff_router)
app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static",
)
# Vite 构建产物中的静态资源
app.mount(
    "/assets",
    StaticFiles(
        directory=STATIC_DIR / "assets",
        check_dir=False,
    ),
    name="assets",
)


@app.get("/", include_in_schema=False)
async def index():
    # 前端调试/演示页面
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/agent", include_in_schema=False)
async def agent_page():
    # 单页应用路由，交给 Vue Router 处理
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


def main() -> None:
    import uvicorn

    from app.conf.config import settings

    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
    )


if __name__ == "__main__":
    main()