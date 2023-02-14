from scheduler import context

from . import App

if __name__ == "__main__":
    app = App(context.AppContext())
    app.run()
