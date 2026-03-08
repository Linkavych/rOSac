import socket
import time
from pathlib import Path
import paramiko
from fabric import Connection
from invoke.exceptions import UnexpectedExit
from .base import AbstractTransport, TransportError
from ..models import CommandResult, TargetContext


class SSHTransport(AbstractTransport):
    SUPPRESS_PAGING_SUFFIX = " without-paging"

    def __init__(
        self,
        target: TargetContext,
        keyfile: str | None = None,
        password: str | None = None,
        passphrase: str | None = None,
        connect_timeout: int = 30,
        command_timeout: int = 60,
    ):
        super().__init__(target)
        self._keyfile = keyfile
        self._password = password
        self._passphrase = passphrase
        self._connect_timeout = connect_timeout
        self._command_timeout = command_timeout
        self._conn: Connection | None = None

    def connect(self) -> None:
        # Build connect_kwargs correctly -- never pass password as keyfile
        connect_kwargs: dict = {"timeout": self._connect_timeout}
        if self._keyfile:
            connect_kwargs["key_filename"] = self._keyfile
            if self._passphrase:
                connect_kwargs["passphrase"] = self._passphrase
        elif self._password:
            connect_kwargs["password"] = self._password

        try:
            self._conn = Connection(
                host=self.target.host,
                port=self.target.port,
                user=self.target.username,
                connect_kwargs=connect_kwargs,
            )
            self._conn.open()
        except (paramiko.SSHException, socket.timeout, OSError) as e:
            raise TransportError(f"SSH connection to {self.target.host} failed: {e}") from e

    def disconnect(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def _ensure_paging_suppressed(self, command: str) -> str:
        if command.startswith("/") and "without-paging" not in command:
            return command.rstrip() + self.SUPPRESS_PAGING_SUFFIX
        return command

    def run(self, command: str) -> CommandResult:
        if not self._conn:
            raise TransportError("Not connected")
        command = self._ensure_paging_suppressed(command)
        start = time.monotonic()
        try:
            result = self._conn.run(command, hide="both", timeout=self._command_timeout, warn=True)
            duration_ms = (time.monotonic() - start) * 1000
            return CommandResult(
                command=command,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.return_code,
                duration_ms=duration_ms,
            )
        except UnexpectedExit as e:
            duration_ms = (time.monotonic() - start) * 1000
            return CommandResult(
                command=command,
                stdout=e.result.stdout if e.result else "",
                stderr=e.result.stderr if e.result else "",
                exit_code=e.result.return_code if e.result else -1,
                duration_ms=duration_ms,
                error=str(e),
            )
        except (socket.timeout, paramiko.SSHException, OSError) as e:
            raise TransportError(f"Command failed on {self.target.host}: {e}") from e

    def get_file(self, remote_path: str, local_path: Path) -> None:
        if not self._conn:
            raise TransportError("Not connected")
        try:
            self._conn.get(remote_path, local=str(local_path))
        except (OSError, paramiko.SSHException) as e:
            raise TransportError(f"File transfer failed for {remote_path}: {e}") from e
