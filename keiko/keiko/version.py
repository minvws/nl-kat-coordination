"""Version information for keiko."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("keiko")
except PackageNotFoundError:
    # package is not installed
    __version__ = "0.0.1.dev1"
