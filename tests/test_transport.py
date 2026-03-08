import pytest
from unittest.mock import MagicMock, patch
from rosac.transport.ssh import SSHTransport
from rosac.transport.base import TransportError
from rosac.models import TargetContext


@pytest.fixture
def target():
    return TargetContext(host="192.168.1.1", username="admin")


def test_ssh_paging_suppressed(target):
    t = SSHTransport(target, keyfile="/fake/key")
    cmd = t._ensure_paging_suppressed("/ip arp print detail")
    assert "without-paging" in cmd


def test_ssh_paging_not_duplicated(target):
    t = SSHTransport(target, keyfile="/fake/key")
    cmd = t._ensure_paging_suppressed("/ip arp print detail without-paging")
    assert cmd.count("without-paging") == 1


def test_ssh_non_ros_command_unchanged(target):
    t = SSHTransport(target, keyfile="/fake/key")
    cmd = t._ensure_paging_suppressed("echo hello")
    assert "without-paging" not in cmd


def test_ssh_run_without_connect(target):
    t = SSHTransport(target, keyfile="/fake/key")
    with pytest.raises(TransportError, match="Not connected"):
        t.run("/ip arp print detail")
