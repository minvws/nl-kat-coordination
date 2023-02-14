from boefjes.plugin_repository.api import create_app
from boefjes.plugin_repository.config import PLUGINS_DIR


app = create_app(PLUGINS_DIR)
