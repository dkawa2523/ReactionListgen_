from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
import re
import unicodedata

import yaml

from .formula import parse_species_token


_GREEK_REPLACEMENTS = {
    "Α": "Alpha",
    "α": "alpha",
    "Β": "Beta",
    "β": "beta",
    "Γ": "Gamma",
    "γ": "gamma",
    "Δ": "Delta",
    "δ": "delta",
    "Λ": "Lambda",
    "λ": "lambda",
    "Π": "Pi",
    "π": "pi",
    "Σ": "Sigma",
    "σ": "sigma",
}

_SUPERSCRIPT_TRANSLATION = str.maketrans(
    {
        "⁰": "0",
        "¹": "1",
        "²": "2",
        "³": "3",
        "⁴": "4",
        "⁵": "5",
        "⁶": "6",
        "⁷": "7",
        "⁸": "8",
        "⁹": "9",
    }
)

_TOKEN_BUCKET_RE = re.compile(r"\*\[[^\]]+\]$|\*$")


def normalize_excitation_label(label: str) -> str:
    text = unicodedata.normalize("NFKC", str(label or "")).translate(_SUPERSCRIPT_TRANSLATION).strip()
    if not text:
        return ""
    for raw, replacement in _GREEK_REPLACEMENTS.items():
        text = text.replace(raw, replacement)
    text = (
        text.replace("−", " minus ")
        .replace("-", " minus ")
        .replace("+", " plus ")
        .replace("^", " ")
        .replace("{", " ")
        .replace("}", " ")
        .replace("_", " ")
        .replace("/", " ")
    )
    text = re.sub(r"[^0-9A-Za-z]+", " ", text)
    return "".join(text.lower().split())


def strip_excitation_suffix(token: str) -> str:
    parsed = parse_species_token(token)
    normalized = parsed.normalized_label
    if parsed.excitation_label:
        return normalized.rsplit("[", 1)[0]
    return _TOKEN_BUCKET_RE.sub("", normalized)


@dataclass(slots=True)
class ExcitedStateRegistryEntry:
    canonical_key: str
    source_aliases: Dict[str, List[str]] = field(default_factory=dict)
    label_synonyms: List[str] = field(default_factory=list)
    excitation_energy_ev: Optional[float] = None
    energy_tolerance_ev: Optional[float] = None
    priority_source: Optional[str] = None

    def as_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class ExcitedStateRegistry:
    entries: List[ExcitedStateRegistryEntry] = field(default_factory=list)
    _entries_by_key: Dict[str, ExcitedStateRegistryEntry] = field(init=False, default_factory=dict, repr=False)
    _entries_by_base_charge: Dict[Tuple[str, int], List[ExcitedStateRegistryEntry]] = field(init=False, default_factory=dict, repr=False)
    _alias_lookup: Dict[str, str] = field(init=False, default_factory=dict, repr=False)
    _source_alias_lookup: Dict[Tuple[str, str], str] = field(init=False, default_factory=dict, repr=False)
    _label_lookup: Dict[str, set[str]] = field(init=False, default_factory=dict, repr=False)
    _alias_keys_by_entry: Dict[str, set[str]] = field(init=False, default_factory=dict, repr=False)
    _source_alias_keys_by_entry: Dict[str, set[Tuple[str, str]]] = field(init=False, default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self._entries_by_key = {
            entry.canonical_key: entry for entry in self.entries
        }
        self._entries_by_base_charge = {}
        self._alias_lookup = {}
        self._source_alias_lookup = {}
        self._label_lookup = {}
        self._alias_keys_by_entry = {}
        self._source_alias_keys_by_entry = {}
        for entry in self.entries:
            parsed = parse_species_token(entry.canonical_key)
            base_key = strip_excitation_suffix(entry.canonical_key)
            self._entries_by_base_charge.setdefault((base_key, parsed.charge), []).append(entry)

            label_keys = {normalize_excitation_label(parsed.excitation_label or "")}
            label_keys.update(
                normalize_excitation_label(label)
                for label in entry.label_synonyms
                if normalize_excitation_label(label)
            )
            self._label_lookup[entry.canonical_key] = label_keys

            alias_keys = {_normalize_text_key(entry.canonical_key)}
            source_alias_keys: set[Tuple[str, str]] = set()
            for source_name, aliases in entry.source_aliases.items():
                normalized_source = _normalize_source(source_name)
                for alias in aliases:
                    alias_key = _normalize_text_key(alias)
                    if not alias_key:
                        continue
                    alias_keys.add(alias_key)
                    if normalized_source:
                        source_alias_keys.add((normalized_source, alias_key))
                        self._source_alias_lookup[(normalized_source, alias_key)] = entry.canonical_key
                    self._alias_lookup.setdefault(alias_key, entry.canonical_key)
            self._alias_keys_by_entry[entry.canonical_key] = alias_keys
            self._source_alias_keys_by_entry[entry.canonical_key] = source_alias_keys
            for alias_key in alias_keys:
                self._alias_lookup.setdefault(alias_key, entry.canonical_key)

    @classmethod
    def empty(cls) -> "ExcitedStateRegistry":
        return cls(entries=[])

    @classmethod
    def from_path(cls, path: Optional[str]) -> "ExcitedStateRegistry":
        if not path:
            return cls.empty()
        target = Path(path)
        if not target.exists():
            raise FileNotFoundError(f"Excited-state registry not found: {target}")
        payload = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
        raw_entries = payload.get("excited_state_registry", payload)
        entries: List[ExcitedStateRegistryEntry] = []
        for raw in raw_entries or []:
            if not isinstance(raw, dict):
                continue
            source_aliases = {
                str(source): _coerce_alias_list(values)
                for source, values in dict(raw.get("source_aliases", {})).items()
            }
            entries.append(
                ExcitedStateRegistryEntry(
                    canonical_key=str(raw["canonical_key"]),
                    source_aliases=source_aliases,
                    label_synonyms=[str(item) for item in raw.get("label_synonyms", []) if item],
                    excitation_energy_ev=(
                        float(raw["excitation_energy_ev"])
                        if raw.get("excitation_energy_ev") is not None
                        else None
                    ),
                    energy_tolerance_ev=(
                        float(raw["energy_tolerance_ev"])
                        if raw.get("energy_tolerance_ev") is not None
                        else None
                    ),
                    priority_source=str(raw["priority_source"]) if raw.get("priority_source") else None,
                )
            )
        return cls(entries=entries)

    def entry_count(self) -> int:
        return len(self.entries)

    def as_dict(self) -> Dict[str, object]:
        return {
            "excited_state_registry": [entry.as_dict() for entry in self.entries],
        }

    def get(self, canonical_key: str) -> Optional[ExcitedStateRegistryEntry]:
        return self._entries_by_key.get(canonical_key)

    def canonicalize_token(
        self,
        token: str,
        *,
        source_system: Optional[str] = None,
        base_species_key: Optional[str] = None,
        excitation_energy_ev: Optional[float] = None,
    ) -> Optional[str]:
        entry = self.lookup(
            token,
            source_system=source_system,
            base_species_key=base_species_key,
            excitation_energy_ev=excitation_energy_ev,
        )
        return entry.canonical_key if entry is not None else None

    def lookup(
        self,
        token: str,
        *,
        source_system: Optional[str] = None,
        base_species_key: Optional[str] = None,
        excitation_energy_ev: Optional[float] = None,
    ) -> Optional[ExcitedStateRegistryEntry]:
        if not self.entries:
            return None
        alias_key = _normalize_text_key(token)
        source_key = _normalize_source(source_system)
        if source_key:
            canonical_key = self._source_alias_lookup.get((source_key, alias_key))
            if canonical_key:
                return self._entries_by_key[canonical_key]
        canonical_key = self._alias_lookup.get(alias_key)
        if canonical_key:
            return self._entries_by_key[canonical_key]

        parsed = parse_species_token(token)
        if not parsed.tracked or not parsed.excitation_label:
            return None
        return self.lookup_label(
            base_species_key=base_species_key or strip_excitation_suffix(parsed.normalized_label),
            charge=parsed.charge,
            label=parsed.excitation_label,
            source_system=source_system,
            excitation_energy_ev=(
                excitation_energy_ev
                if excitation_energy_ev is not None
                else parsed.excitation_energy_ev
            ),
            raw_alias_key=alias_key,
        )

    def lookup_label(
        self,
        *,
        base_species_key: str,
        charge: int,
        label: Optional[str],
        source_system: Optional[str] = None,
        excitation_energy_ev: Optional[float] = None,
        raw_alias_key: Optional[str] = None,
    ) -> Optional[ExcitedStateRegistryEntry]:
        if not label:
            return None
        label_key = normalize_excitation_label(label)
        if not label_key:
            return None
        candidates = self._entries_by_base_charge.get((base_species_key, charge), [])
        best_entry: Optional[ExcitedStateRegistryEntry] = None
        best_key: Optional[Tuple[int, int, float, str]] = None
        source_key = _normalize_source(source_system)
        alias_key = raw_alias_key or ""
        for entry in candidates:
            if label_key not in self._label_lookup.get(entry.canonical_key, set()):
                continue
            energy_distance = _energy_distance(entry, excitation_energy_ev)
            if energy_distance is None:
                continue
            source_alias_score = 1 if source_key and (source_key, alias_key) in self._source_alias_keys_by_entry.get(entry.canonical_key, set()) else 0
            alias_score = 1 if alias_key and alias_key in self._alias_keys_by_entry.get(entry.canonical_key, set()) else 0
            priority_score = 1 if source_key and _normalize_source(entry.priority_source) == source_key else 0
            candidate_key = (
                source_alias_score,
                priority_score,
                alias_score,
                -energy_distance,
                entry.canonical_key,
            )
            if best_key is None or candidate_key > best_key:
                best_key = candidate_key
                best_entry = entry
        return best_entry


def _coerce_alias_list(values: object) -> List[str]:
    if values is None:
        return []
    if isinstance(values, str):
        return [values]
    if isinstance(values, Sequence):
        return [str(item) for item in values if item]
    return [str(values)]


def _energy_distance(
    entry: ExcitedStateRegistryEntry,
    candidate_energy_ev: Optional[float],
) -> Optional[float]:
    if candidate_energy_ev is None or entry.excitation_energy_ev is None:
        return 0.0
    tolerance = entry.energy_tolerance_ev if entry.energy_tolerance_ev is not None else 0.0
    delta = abs(candidate_energy_ev - entry.excitation_energy_ev)
    if tolerance and delta > tolerance:
        return None
    if not tolerance and delta > 1e-9:
        return None
    return delta


def _normalize_source(source_system: Optional[str]) -> str:
    return str(source_system or "").strip().lower()


def _normalize_text_key(token: str) -> str:
    return "".join(unicodedata.normalize("NFKC", str(token or "")).split()).lower()
