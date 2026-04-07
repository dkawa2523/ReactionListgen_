from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional
import json

import yaml

from .catalog import TemplateCatalog
from .excited_state_registry import ExcitedStateRegistry
from .formula import parse_species_token


@dataclass(slots=True)
class AliasResolver:
    """Simple alias resolver for reaction/species tokens.

    The resolver keeps the behavior intentionally small and explicit:
    - packaged safe aliases are always loaded
    - species_library aliases are opt-in through ``from_catalog``
    - project-specific aliases can be layered from YAML/JSON

    Alias mapping is one-way: alias -> canonical token.
    """

    alias_map: Dict[str, str]
    excited_state_registry: ExcitedStateRegistry = field(default_factory=ExcitedStateRegistry.empty)

    @classmethod
    def empty(cls) -> "AliasResolver":
        return cls(alias_map={}, excited_state_registry=ExcitedStateRegistry.empty())

    @classmethod
    def from_catalog(
        cls,
        catalog: Optional[TemplateCatalog] = None,
        *,
        alias_path: Optional[str] = None,
        excited_state_registry: Optional[ExcitedStateRegistry] = None,
    ) -> "AliasResolver":
        mapping: Dict[str, str] = {}
        mapping.update(_load_packaged_aliases())
        if catalog is not None:
            for proto in catalog.species_library.values():
                for alias in proto.aliases:
                    if alias and alias != proto.key:
                        mapping[alias] = proto.key
        if alias_path:
            mapping.update(_load_alias_file(alias_path))
        return cls(
            alias_map=mapping,
            excited_state_registry=excited_state_registry or ExcitedStateRegistry.empty(),
        )

    def as_dict(self) -> Dict[str, str]:
        return dict(sorted(self.alias_map.items(), key=lambda item: item[0].lower()))

    def canonicalize_tokens(self, tokens: Iterable[str], *, source_system: Optional[str] = None) -> List[str]:
        return [self.canonicalize_token(token, source_system=source_system) for token in tokens]

    def canonicalize_token(self, token: str, *, source_system: Optional[str] = None) -> str:
        raw = token.strip()
        if not raw:
            return raw

        registry_match = self.excited_state_registry.canonicalize_token(raw, source_system=source_system)
        if registry_match:
            return registry_match

        direct = self._lookup(raw)
        if direct:
            registry_match = self.excited_state_registry.canonicalize_token(direct, source_system=source_system)
            return registry_match or direct

        parsed = parse_species_token(raw)
        base = parsed.formula or parsed.normalized_label
        canonical_base = self._lookup(base)
        if not canonical_base:
            return raw

        # Preserve charge and simple excitation labeling while replacing the base token.
        rebuilt = _rebuild_from_parsed(canonical_base, parsed)
        registry_match = self.excited_state_registry.canonicalize_token(rebuilt, source_system=source_system)
        return registry_match or rebuilt

    def _lookup(self, token: str) -> Optional[str]:
        if token in self.alias_map:
            return self.alias_map[token]
        lowered = token.lower()
        for alias, canonical in self.alias_map.items():
            if alias.lower() == lowered:
                return canonical
        return None


SAFE_PACKAGED_ALIASES = {
    "e": "e-",
    "electron": "e-",
    "Electron": "e-",
    "hv": "hν",
    "photon": "hν",
    "Photon": "hν",
}


def _load_packaged_aliases() -> Dict[str, str]:
    return dict(SAFE_PACKAGED_ALIASES)


def _load_alias_file(path: str) -> Dict[str, str]:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"Alias file not found: {target}")
    if target.suffix.lower() == ".json":
        payload = json.loads(target.read_text(encoding="utf-8"))
    else:
        payload = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    aliases = payload.get("aliases", payload)
    out: Dict[str, str] = {}
    if isinstance(aliases, dict):
        for alias, canonical in aliases.items():
            if alias and canonical:
                out[str(alias)] = str(canonical)
    elif isinstance(aliases, list):
        for entry in aliases:
            if not isinstance(entry, dict):
                continue
            alias = entry.get("alias") or entry.get("from")
            canonical = entry.get("canonical") or entry.get("to")
            if alias and canonical:
                out[str(alias)] = str(canonical)
    return out


def _rebuild_from_parsed(canonical_base: str, parsed) -> str:
    rebuilt = canonical_base
    if parsed.charge > 0:
        rebuilt += "+" * parsed.charge
    elif parsed.charge < 0:
        rebuilt += "-" * abs(parsed.charge)
    if parsed.excitation_label:
        rebuilt += f"[{parsed.excitation_label}]"
    elif parsed.excitation_energy_ev is not None and parsed.state_class == "excited_bucket":
        rebuilt += f"*[{parsed.excitation_energy_ev:g}eV]"
    elif parsed.state_class == "excited_bucket":
        rebuilt += "*"
    return rebuilt
