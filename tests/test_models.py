from rosac.models import (
    ArtifactDocument, TargetContext, CommandResult, Finding, Severity, RosVersion
)
from datetime import datetime


def test_artifact_document_roundtrip():
    target = TargetContext(host="192.168.1.1", username="admin")
    doc = ArtifactDocument(
        target=target,
        collector="volatile.active_connections",
        category="volatile",
        volatility=1,
        raw="/ip firewall connection print detail output...",
    )
    serialized = doc.model_dump(mode="json")
    restored = ArtifactDocument.model_validate(serialized)
    assert restored.collector == doc.collector
    assert restored.target.host == "192.168.1.1"
    assert restored.schema_version == "1.0"


def test_finding_severity():
    f = Finding(rule="test_rule", severity=Severity.HIGH, message="Test finding")
    assert f.severity == "high"


def test_ros_version_comparison():
    v1 = RosVersion(raw="7.14.3", major=7, minor=14, patch=3)
    v2 = RosVersion(raw="6.49.15", major=6, minor=49, patch=15)
    assert v1 >= v2
    assert v2 < v1
