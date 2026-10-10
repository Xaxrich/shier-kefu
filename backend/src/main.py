"""智能客服后端入口：FastAPI + PyCore APIServer。"""

from pycore.api import APIConfig, APIServer
from pycore.core import Logger, LoggerConfig, LogLevel, get_logger

from src.api.routes.auth import router as auth_router
from src.api.routes.kb import router as kb_router
from src.api.routes.tickets import router as tickets_router
from src.core.settings import get_settings
from src.db.session import close_db, init_db

settings = get_settings()

Logger.configure(LoggerConfig(level=LogLevel.INFO, app_name="shier-kefu", json_format=False))
logger = get_logger()

server = APIServer(
    APIConfig(
        title="智能客服 API",
        version="0.1.0",
        debug=settings.debug,
        cors_origins=settings.cors_origins,
    )
)

server.on_startup(init_db)
server.on_shutdown(close_db)
server.include_router(auth_router)
server.include_router(tickets_router)
server.include_router(kb_router)

app = server.app

logger.info("Application factory ready")
