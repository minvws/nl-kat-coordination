"""Entrypoint for the octopoes package."""
from octopoes.app import App
from octopoes.context.context import AppContext


if __name__ == "__main__":
    app = App(AppContext())
    app.run()
