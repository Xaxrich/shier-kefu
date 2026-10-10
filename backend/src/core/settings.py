"""应用配置：从 backend/config.toml 经 PyCore ConfigManager 加载。"""

from pathlib import Path

from pycore.core import BaseSettings, ConfigManager

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = BACKEND_ROOT / "config.toml"


def _load_dotenv() -> None:
    """加载 backend/.env 到进程环境（若存在且已安装 python-dotenv）。密钥只放此文件，勿提交。"""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    p = BACKEND_ROOT / ".env"
    if p.is_file():
        load_dotenv(p)


_load_dotenv()


class AppSettings(BaseSettings):
    debug: bool = False
    secret_key: str = "change-me"
    database_url: str = "sqlite+aiosqlite:///./app.db"
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["http://localhost:5173"]
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 10080
    kb_storage_dir: str = "data/kb"
    kb_max_upload_bytes: int = 2_097_152
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_chat_model: str = "gpt-4o-mini"
    llm_embedding_model: str = "text-embedding-3-small"
    qa_similarity_threshold: float = 0.8
    rrf_k: int = 60
    vector_top_k: int = 5
    keyword_top_k: int = 8
    rerank_top_k: int = 5


_settings: AppSettings | None = None


def get_settings() -> AppSettings:
    global _settings
    if _settings is None:
        cm = ConfigManager[AppSettings]()
        cm.load(AppSettings, CONFIG_PATH)
        _settings = cm.settings
    return _settings
