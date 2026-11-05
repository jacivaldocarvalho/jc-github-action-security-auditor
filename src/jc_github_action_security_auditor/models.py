"""Data models for security findings."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class Severity(Enum):
    """Severity of a security finding."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class Finding:
    """A security finding associated with a workflow file."""

    rule_id: str
    severity: Severity
    message: str
    file_path: Path
    line: int | None = None
    recommendation: str | None = None
