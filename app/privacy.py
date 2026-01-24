"""Privacy protection: redaction, allowlists, and hashing."""
import hashlib
import logging
import re
from typing import Optional

from app.settings import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Allowlist of safe flag names (no values, just names)
ALLOWED_FLAG_PATTERNS = [
    r"^--?[a-zA-Z][a-zA-Z0-9_-]*$",  # Standard flags like --help, -v, --dry-run
]

# Blocklist patterns for flag names that might leak sensitive info
BLOCKED_FLAG_PATTERNS = [
    r"(?i)token",
    r"(?i)password",
    r"(?i)secret",
    r"(?i)key",
    r"(?i)auth",
    r"(?i)credential",
    r"(?i)api[-_]?key",
]

# Patterns to redact from error_type
ERROR_REDACTION_PATTERNS = [
    r"/[^\s]+",  # File paths
    r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",  # Emails
    r"\b[A-Za-z0-9+/]{20,}={0,2}\b",  # Base64-like tokens
    r"\b[0-9a-fA-F]{32,}\b",  # Hex tokens (API keys, etc.)
]

# Safe command names (allowlist for command_path elements)
SAFE_COMMAND_PATTERN = r"^[a-zA-Z][a-zA-Z0-9_-]*$"


def hash_identifier(value: str) -> str:
    """
    Hash an identifier (actor_id, machine_id) for privacy.
    Uses SHA-256 with a salt.
    """
    if not value:
        return hashlib.sha256(settings.hash_salt.encode()).hexdigest()[:16]

    salted = f"{settings.hash_salt}:{value}"
    return hashlib.sha256(salted.encode()).hexdigest()[:16]


def sanitize_flag_name(flag: str) -> Optional[str]:
    """
    Sanitize a flag name. Returns None if flag should be blocked.
    """
    # Strip any value that might have leaked through
    flag_name = flag.split("=")[0].split(":")[0].strip()

    if not flag_name:
        return None

    # Check blocklist first
    for pattern in BLOCKED_FLAG_PATTERNS:
        if re.search(pattern, flag_name):
            logger.debug(f"Blocked sensitive flag: {flag_name[:10]}...")
            return None

    # Validate against allowlist patterns
    for pattern in ALLOWED_FLAG_PATTERNS:
        if re.match(pattern, flag_name):
            return flag_name

    # If doesn't match standard flag pattern, reject
    logger.debug(f"Rejected non-standard flag: {flag_name[:10]}...")
    return None


def sanitize_flags(flags: list[str]) -> list[str]:
    """Sanitize a list of flag names."""
    sanitized = []
    for flag in flags:
        clean_flag = sanitize_flag_name(flag)
        if clean_flag:
            sanitized.append(clean_flag)
    return sanitized


def sanitize_command_path(path: list[str]) -> list[str]:
    """
    Sanitize command path elements.
    Only allows alphanumeric command names to prevent path leakage.
    """
    sanitized = []
    for element in path:
        element = str(element).strip()
        if re.match(SAFE_COMMAND_PATTERN, element):
            sanitized.append(element.lower())  # Normalize to lowercase
        else:
            # Replace with redacted marker but keep position info
            sanitized.append("[REDACTED]")
    return sanitized


def sanitize_error_type(error_type: Optional[str]) -> Optional[str]:
    """
    Sanitize error type string by removing sensitive patterns.
    """
    if not error_type:
        return None

    result = error_type

    for pattern in ERROR_REDACTION_PATTERNS:
        result = re.sub(pattern, "[REDACTED]", result)

    # Truncate to max length
    if len(result) > 256:
        result = result[:253] + "..."

    return result


def sanitize_tool_name(tool_name: str) -> str:
    """Sanitize tool name to prevent injection."""
    # Only allow alphanumeric, dash, underscore
    clean = re.sub(r"[^a-zA-Z0-9_-]", "", tool_name)
    return clean[:128] if clean else "unknown"


def sanitize_tool_version(version: Optional[str]) -> Optional[str]:
    """Sanitize version string."""
    if not version:
        return None
    # Only allow version-like patterns
    clean = re.sub(r"[^a-zA-Z0-9._-]", "", version)
    return clean[:64] if clean else None
