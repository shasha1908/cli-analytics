"""CLI Analytics tracker."""
import hashlib
import os
import platform
import time
from datetime import datetime, timezone
from typing import Optional
import httpx


def _get_actor_id() -> str:
    return os.environ.get("USER", os.environ.get("USERNAME", "unknown"))


def _get_machine_id() -> str:
    return platform.node()


def _detect_ci() -> bool:
    ci_vars = ["CI", "GITHUB_ACTIONS", "GITLAB_CI", "CIRCLECI", "JENKINS_URL", "TRAVIS"]
    return any(os.environ.get(v) for v in ci_vars)


class Tracker:
    """CLI Analytics tracker client."""

    def __init__(self, api_key: str, endpoint: str = "https://cli-analytics.onrender.com"):
        self.api_key = api_key
        self.endpoint = endpoint.rstrip("/")
        self.tool_name: Optional[str] = None
        self.tool_version: Optional[str] = None

    def configure(self, tool_name: str, tool_version: Optional[str] = None):
        """Configure the tracker with tool info."""
        self.tool_name = tool_name
        self.tool_version = tool_version

    def track(
        self,
        command_path: list,
        exit_code: Optional[int] = None,
        duration_ms: Optional[int] = None,
        flags: Optional[list] = None,
        error_type: Optional[str] = None,
    ):
        """Track a CLI command execution."""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tool_name": self.tool_name or "unknown",
            "tool_version": self.tool_version,
            "command_path": command_path,
            "flags_present": flags or [],
            "exit_code": exit_code,
            "duration_ms": duration_ms,
            "error_type": error_type,
            "actor_id": _get_actor_id(),
            "machine_id": _get_machine_id(),
            "ci_detected": _detect_ci(),
        }

        try:
            httpx.post(
                f"{self.endpoint}/ingest",
                json=event,
                headers={"X-API-Key": self.api_key},
                timeout=5.0,
            )
        except Exception:
            pass  # Fail silently - analytics should never break the CLI


# Global tracker instance
_tracker: Optional[Tracker] = None


def init(api_key: str, tool_name: str, tool_version: Optional[str] = None, endpoint: Optional[str] = None):
    """Initialize the global tracker."""
    global _tracker
    _tracker = Tracker(api_key, endpoint or "https://cli-analytics.onrender.com")
    _tracker.configure(tool_name, tool_version)


def track_command(command_path: list, exit_code: Optional[int] = None, **kwargs):
    """Track a command using the global tracker."""
    if _tracker:
        _tracker.track(command_path, exit_code, **kwargs)
