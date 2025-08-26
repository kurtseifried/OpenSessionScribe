"""OpenSessionScribe - Local podcast and webinar processing toolkit."""

__version__ = "0.1.0"

from .pipeline import ProcessingPipeline
from .config import Config

__all__ = ["ProcessingPipeline", "Config"]