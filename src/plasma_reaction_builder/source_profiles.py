from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files as resource_files
from pathlib import Path
from typing import Dict, Optional
import json

import yaml


@dataclass(slots=True)
class SourceProfile:
    source_id: str
    family: str
    default_support: float
    priority: int = 50
    note: Optional[str] = None

    def as_dict(self) -> Dict[str, object]:
        return {
            "source_id": self.source_id,
            "family": self.family,
            "default_support": self.default_support,
            "priority": self.priority,
            "note": self.note,
        }


class SourceStrengthRegistry:
    def __init__(self, profiles: Dict[str, SourceProfile]) -> None:
        self.profiles = {key.lower(): value for key, value in profiles.items()}

    @classmethod
    def from_path(cls, path: Optional[str] = None) -> "SourceStrengthRegistry":
        payload = _load_packaged_profiles()
        if path:
            payload = _merge_profiles(payload, _load_profile_file(path))
        profiles: Dict[str, SourceProfile] = {}
        for entry in payload.get("profiles", []):
            profile = SourceProfile(**entry)
            profiles[profile.source_id.lower()] = profile
        return cls(profiles)

    def profile_for(self, source_id: Optional[str]) -> Optional[SourceProfile]:
        if not source_id:
            return None
        return self.profiles.get(source_id.lower())

    def apply(self, source_id: Optional[str], support_score: Optional[float]) -> float:
        profile = self.profile_for(source_id)
        if profile is None:
            if support_score is None:
                return 0.60
            return _clamp(float(support_score))
        if support_score is None:
            return _clamp(profile.default_support)
        # Mild blend keeps adapter-specific information while nudging by source strength.
        blended = 0.7 * float(support_score) + 0.3 * profile.default_support
        return _clamp(blended)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _load_packaged_profiles() -> Dict[str, object]:
    resource = resource_files("plasma_reaction_builder.data").joinpath("source_profiles.yaml")
    return yaml.safe_load(resource.read_text(encoding="utf-8")) or {"profiles": []}


def _load_profile_file(path: str) -> Dict[str, object]:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"Source profile file not found: {target}")
    if target.suffix.lower() == ".json":
        return json.loads(target.read_text(encoding="utf-8"))
    return yaml.safe_load(target.read_text(encoding="utf-8")) or {"profiles": []}


def _merge_profiles(base: Dict[str, object], override: Dict[str, object]) -> Dict[str, object]:
    merged = {"profiles": list(base.get("profiles", []))}
    seen = {entry["source_id"].lower(): idx for idx, entry in enumerate(merged["profiles"]) if isinstance(entry, dict) and entry.get("source_id")}
    for entry in override.get("profiles", []):
        if not isinstance(entry, dict) or not entry.get("source_id"):
            continue
        key = entry["source_id"].lower()
        if key in seen:
            merged["profiles"][seen[key]] = entry
        else:
            seen[key] = len(merged["profiles"])
            merged["profiles"].append(entry)
    return merged
