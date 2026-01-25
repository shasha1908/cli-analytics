"""CLI Analytics SDK - Track CLI tool usage with privacy-first analytics."""
from .tracker import Tracker, init, track_command, get_variant, get_recommendation

__all__ = ["Tracker", "init", "track_command", "get_variant", "get_recommendation"]
__version__ = "0.1.0"
