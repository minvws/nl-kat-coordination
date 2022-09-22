from os import getenv
from pathlib import Path

BASE_DIR = Path(__file__).parent
PLUGINS_DIR = Path(getenv("PLUGINS_DIR", BASE_DIR.parent / "plugins"))
PLUGINS_DIR.mkdir(exist_ok=True)
BASE_URL = getenv("BASE_URL", "http://localhost")
