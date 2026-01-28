import os
import sys
import platform
from dotenv import load_dotenv

load_dotenv()


def _resolve_data_dir():
    """Return the data directory, adapting for PyInstaller bundles."""
    if getattr(sys, '_MEIPASS', None):
        # Running as a PyInstaller bundle — store user data in platform dir
        system = platform.system()
        if system == "Darwin":
            base = os.path.join(os.path.expanduser("~"),
                                "Library", "Application Support", "OpenChatDB")
        elif system == "Windows":
            base = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")),
                                "OpenChatDB")
        else:
            base = os.path.join(os.path.expanduser("~"), ".openchatdb")
        return base
    # Development mode — keep data alongside the source
    return os.path.join(os.path.dirname(__file__), "data")


class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
    DATA_DIR = _resolve_data_dir()
    CONNECTIONS_FILE = os.path.join(DATA_DIR, "connections.json")

    # LLM
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "4096"))
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0"))
