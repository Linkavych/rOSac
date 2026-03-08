from __future__ import annotations
from pathlib import Path
import time
from .base import AbstractTransport, TransportError, TransportNotAvailable
from ..models import CommandResult, TargetContext


def _require_librouteros():
    try:
        import librouteros
        return librouteros
    except ImportError:
        raise TransportNotAvailable(
            "librouteros is required for the API transport. "
            "Install it with: pip install 'rosac[api]'"
        )


class APITransport(AbstractTransport):
    """
    RouterOS API transport using librouteros.
    Translates CLI-style commands to API calls.
    Note: Not all CLI commands have API equivalents.
    Falls back gracefully with a warning for untranslatable commands.
    """

    def __init__(
        self,
        target: TargetContext,
        password: str = "",
        api_port: int = 8728,
        use_ssl: bool = False,
    ):
        super().__init__(target)
        self._password = password
        self._api_port = api_port
        self._use_ssl = use_ssl
        self._api = None

    def connect(self) -> None:
        lib = _require_librouteros()
        try:
            if self._use_ssl:
                import ssl
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                self._api = lib.connect(
                    self.target.host,
                    username=self.target.username,
                    password=self._password,
                    port=self._api_port,
                    ssl_wrapper=ctx.wrap_socket,
                )
            else:
                self._api = lib.connect(
                    self.target.host,
                    username=self.target.username,
                    password=self._password,
                    port=self._api_port,
                )
        except Exception as e:
            raise TransportError(f"RouterOS API connection to {self.target.host} failed: {e}") from e

    def disconnect(self) -> None:
        if self._api:
            try:
                self._api.close()
            except Exception:
                pass
            self._api = None

    def _cli_to_api(self, command: str) -> tuple[str, dict] | None:
        """
        Translate a RouterOS CLI command to API path + parameters.
        Returns (api_path, params) or None if not translatable.

        Example: '/ip arp print detail' -> ('/ip/arp/print', {})
        """
        command = command.replace(" without-paging", "").strip()
        if not command.startswith("/"):
            return None

        parts = command.lstrip("/").split()
        if not parts:
            return None

        # Find 'print' verb and build API path
        if "print" in parts:
            print_idx = parts.index("print")
            path_parts = parts[:print_idx]
            api_path = "/" + "/".join(path_parts) + "/print"
            return api_path, {}

        return None

    def run(self, command: str) -> CommandResult:
        if not self._api:
            raise TransportError("Not connected")

        start = time.monotonic()
        translated = self._cli_to_api(command)

        if translated is None:
            return CommandResult(
                command=command,
                stdout="",
                stderr=f"Command not translatable to RouterOS API: {command}",
                exit_code=-1,
                duration_ms=0.0,
                error="not_translatable",
            )

        api_path, params = translated
        try:
            results = list(self._api(api_path, **params))
            duration_ms = (time.monotonic() - start) * 1000
            # Format results as RouterOS-like text output
            lines = []
            for i, item in enumerate(results):
                lines.append(f"  {i}  " + "  ".join(f"{k}={v}" for k, v in item.items()))
            stdout = "\n".join(lines)
            return CommandResult(
                command=command,
                stdout=stdout,
                exit_code=0,
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = (time.monotonic() - start) * 1000
            raise TransportError(f"API command failed: {e}") from e

    def get_file(self, remote_path: str, local_path: Path) -> None:
        # RouterOS API does not support file transfer; use SSH/SFTP for files
        raise TransportError(
            "File transfer is not supported via the RouterOS API transport. "
            "Use SSH transport for file downloads."
        )
