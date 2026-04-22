from importlib.metadata import PackageNotFoundError, version

from .models import MessagesResponse, parse_message

__all__ = ["parse_message", "MessagesResponse"]

try:
    __version__ = version("aleph-message")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"
