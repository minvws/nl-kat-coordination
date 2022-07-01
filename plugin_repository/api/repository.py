from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from plugin_repository.api.routers import plugins, simplestreams
from plugin_repository.version import __version__


def create_app(images_directory: Path):
    app = FastAPI(title="Plugin Repository", version=__version__)
    app.include_router(plugins.router)
    app.include_router(simplestreams.router)
    app.mount("/images", StaticFiles(directory=images_directory), name="images")

    @app.get("/")
    def root():
        return {}

    return app
