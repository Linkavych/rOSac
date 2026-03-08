from __future__ import annotations
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import yaml


class CollectionProfile(BaseModel):
    """Named collection profile -- defines what to collect."""
    categories: list[str] = Field(default_factory=list)  # empty = all
    download_files: bool = False
    system_backup: bool = False
    config_backup: bool = False
    analyze: bool = False
    description: str = ""


# Built-in profiles
BUILTIN_PROFILES: dict[str, CollectionProfile] = {
    "ir-quick": CollectionProfile(
        categories=["volatile", "persistence", "users"],
        analyze=True,
        description="Fast IR triage: volatile data, persistence artifacts, and users only",
    ),
    "full-audit": CollectionProfile(
        categories=[],  # empty = all
        download_files=True,
        config_backup=True,
        analyze=True,
        description="Complete collection of all categories with file download",
    ),
}


class TargetConfig(BaseModel):
    host: str
    port: int = 22
    username: str = ""
    keyfile: str | None = None
    password: str | None = None
    passphrase: str | None = None


class RosacConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ROSAC_",
        env_file=".env",
        extra="ignore",
    )

    # Transport
    transport: str = "ssh"          # "ssh" or "api"
    api_port: int = 8728
    api_tls: bool = False
    connect_timeout: int = 30
    command_timeout: int = 60

    # Collection
    workers: int = 5
    categories: list[str] = Field(default_factory=list)
    download_files: bool = False
    system_backup: bool = False
    config_backup: bool = False
    analyze: bool = False
    profile: str | None = None

    # Output
    output_dir: Path = Path("output")
    compress: bool = True
    compression: str = "gz"         # "gz" or "xz"
    clean_after_compress: bool = False

    # Profiles (loaded from config file)
    profiles: dict[str, CollectionProfile] = Field(default_factory=dict)

    def get_profile(self, name: str) -> CollectionProfile | None:
        if name in BUILTIN_PROFILES:
            return BUILTIN_PROFILES[name]
        return self.profiles.get(name)

    @classmethod
    def from_yaml(cls, path: Path) -> "RosacConfig":
        """Load config from a YAML file."""
        if not path.exists():
            return cls()
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return cls(**data)

    @classmethod
    def load(cls) -> "RosacConfig":
        """Load config from default locations in priority order."""
        # Project-local config takes precedence over user config
        for candidate in [Path("rosac.yaml"), Path.home() / ".rosac" / "config.yaml"]:
            if candidate.exists():
                return cls.from_yaml(candidate)
        return cls()
