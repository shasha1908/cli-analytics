"""CLI Analytics SDK - Track CLI tool usage with privacy-first analytics."""
from .tracker import Tracker, track_command

__all__ = ["Tracker", "track_command"]
__version__ = "0.1.0"
