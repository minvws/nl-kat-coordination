# pylint: disable=missing-module-docstring
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("keiko")
except PackageNotFoundError:
    # package is not installed
    __version__ = "0.0.1.dev1"
