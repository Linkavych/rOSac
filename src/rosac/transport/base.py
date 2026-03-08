from abc import ABC, abstractmethod
from pathlib import Path
from ..models import CommandResult, TargetContext


class TransportError(Exception):
    """Raised when a transport operation fails."""


class TransportNotAvailable(ImportError):
    """Raised when a transport's optional dependency is not installed."""


class AbstractTransport(ABC):
    def __init__(self, target: TargetContext):
        self.target = target

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @abstractmethod
    def run(self, command: str) -> CommandResult: ...

    @abstractmethod
    def get_file(self, remote_path: str, local_path: Path) -> None: ...

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False
