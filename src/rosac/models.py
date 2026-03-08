from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field
import uuid


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    INFO = "info"


class RosVersion(BaseModel):
    raw: str                    # e.g. "7.14.3 (stable)"
    major: int
    minor: int
    patch: int
    channel: str = ""           # stable, beta, rc, etc.

    def __ge__(self, other: RosVersion) -> bool:
        return (self.major, self.minor, self.patch) >= (other.major, other.minor, other.patch)

    def __lt__(self, other: RosVersion) -> bool:
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)


class TargetContext(BaseModel):
    host: str
    port: int = 22
    username: str
    ros_version: RosVersion | None = None
    architecture: str = ""
    identity: str = ""          # router's /system identity name


class CommandResult(BaseModel):
    command: str
    stdout: str
    stderr: str = ""
    exit_code: int = 0
    duration_ms: float = 0.0
    error: str | None = None    # set if command failed


class Finding(BaseModel):
    rule: str
    severity: Severity
    message: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class ArtifactDocument(BaseModel):
    schema_version: str = "1.0"
    collection_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    target: TargetContext
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    collector: str              # dotted path e.g. "volatile.active_connections"
    category: str
    volatility: int = 99
    raw: str
    data: list[dict[str, Any]] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)


class CollectionManifest(BaseModel):
    collection_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    target: TargetContext
    started_at: datetime
    completed_at: datetime | None = None
    artifacts: list[str] = Field(default_factory=list)   # list of artifact collector names
    artifact_hashes: dict[str, str] = Field(default_factory=dict)  # filename -> sha256
    errors: list[str] = Field(default_factory=list)
    findings_count: dict[str, int] = Field(default_factory=dict)   # severity -> count
