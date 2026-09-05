"""Local Configuration & Security Profile Store for CryptaVault."""

from __future__ import annotations

import json
from pathlib import Path

from cryptavault.adaptive.profiles import SecurityProfile, get_profile


class ProfileStore:
    """Manages persistent active profile configuration on the local machine."""

    DEFAULT_CONFIG_DIR = Path.home() / ".cryptavault"
    CONFIG_FILE_NAME = "config.json"

    def __init__(self, config_dir: Path | None = None) -> None:
        self.config_dir = config_dir or self.DEFAULT_CONFIG_DIR
        self.config_file = self.config_dir / self.CONFIG_FILE_NAME

    def get_active_profile(self) -> SecurityProfile:
        """Read active profile from config or return BALANCED by default."""
        if not self.config_file.exists():
            return get_profile("BALANCED")

        try:
            content = json.loads(self.config_file.read_text(encoding="utf-8"))
            profile_name = content.get("active_profile", "BALANCED")
            return get_profile(profile_name)
        except Exception:
            return get_profile("BALANCED")

    def set_active_profile(self, profile_name_or_level: str) -> SecurityProfile:
        """Persist active security profile name."""
        profile = get_profile(profile_name_or_level)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        config_data = {}
        if self.config_file.exists():
            try:
                config_data = json.loads(self.config_file.read_text(encoding="utf-8"))
            except Exception:
                config_data = {}

        config_data["active_profile"] = profile.level.value
        self.config_file.write_text(json.dumps(config_data, indent=2), encoding="utf-8")
        return profile
