"""
应用配置模块
"""
import os
import tempfile
import shutil
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 基础路径
BASE_DIR = Path(__file__).resolve().parent.parent

# 使用临时目录 - 每次重启数据都会重置
# 如果要持久化，将 USE_TEMP_STORAGE 改为 False
USE_TEMP_STORAGE = True

if USE_TEMP_STORAGE:
    # 创建临时目录
    TEMP_DIR = Path(tempfile.gettempdir()) / "论文小助手"
    DATA_DIR = TEMP_DIR / "data"
    # 清理旧的临时数据（如果存在）
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
else:
    DATA_DIR = BASE_DIR / "data"

# 创建必要的目录
(DATA_DIR / "uploads").mkdir(parents=True, exist_ok=True)
(DATA_DIR / "vectors").mkdir(parents=True, exist_ok=True)
(DATA_DIR / "charts").mkdir(parents=True, exist_ok=True)

print(f"🗂️  数据目录: {DATA_DIR}")


class Config:
    """应用配置类"""

    # AI API配置 (支持智谱AI、Kimi、DeepSeek等)
    KIMI_API_KEY = os.getenv("KIMI_API_KEY", "")
    # 智谱AI GLM-4 (推荐)
    KIMI_MODEL = os.getenv("KIMI_MODEL", "glm-4")
    KIMI_BASE_URL = os.getenv("KIMI_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
    # 其他API配置示例：
    # Kimi: KIMI_MODEL=moonshot-v1-128k, KIMI_BASE_URL=https://api.moonshot.cn/v1
    # DeepSeek: KIMI_MODEL=deepseek-chat, KIMI_BASE_URL=https://api.deepseek.com/v1

    # 数据库配置
    DB_PATH = os.getenv("DB_PATH", str(DATA_DIR / "papers.db"))
    VECTOR_INDEX_PATH = os.getenv("VECTOR_INDEX_PATH", str(DATA_DIR / "vectors" / "faiss.index"))

    # 文件存储路径
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", str(DATA_DIR / "uploads"))
    CHART_DIR = os.getenv("CHART_DIR", str(DATA_DIR / "charts"))

    # 文件限制
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "52428800"))  # 50MB
    MAX_PDF_PAGES = int(os.getenv("MAX_PDF_PAGES", "500"))

    # 文本分块配置
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "512"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "128"))

    # 检索配置
    TOP_K_RETRIEVAL = int(os.getenv("TOP_K_RETRIEVAL", "5"))
    SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.6"))

    # 服务器配置
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))
    DEBUG = os.getenv("DEBUG", "true").lower() == "true"


config = Config()