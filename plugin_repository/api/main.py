from plugin_repository.api.repository import create_app
from plugin_repository.config import PLUGINS_DIR


app = create_app(PLUGINS_DIR)
