"""crawldiff — git log for any website."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__: str = version("crawldiff")
except PackageNotFoundError:
    __version__ = "0.0.0"
