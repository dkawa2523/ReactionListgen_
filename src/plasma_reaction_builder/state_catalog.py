from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

import yaml

from .adapters import NistAsdBootstrapAdapter
from .formula import parse_formula, parse_species_token
from .model import SpeciesPrototype


@dataclass(slots=True)
class ExcitedStateSpec:
    label: str
    energy_ev: Optional[float] = None
    charge: int = 0
    display_name: Optional[str] = None
    state_class: str = "excited"
    aliases: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    enabled: bool = True


@dataclass(slots=True)
class StateMasterEntry:
    family: str
    species_id: str
    preferred_key: str
    display_name: str
    formula: str
    aliases: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    allowed_charges: List[int] = field(default_factory=lambda: [0])
    charge_window_min: int = -2
    charge_window_max: int = 2
    excitation_policy: str = "none"
    priority: int = 50
    required_sources: List[str] = field(default_factory=list)
    enabled: bool = True
    nist_query: Optional[str] = None
    structure_id: Optional[str] = None
    multiplicity: Optional[int] = None
    excited_states: List[ExcitedStateSpec] = field(default_factory=list)


def load_state_master(path: str | Path) -> List[StateMasterEntry]:
    target = Path(path)
    payload = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    entries = payload.get("state_master", [])
    materialized: List[StateMasterEntry] = []
    for entry in entries:
        normalized = dict(entry)
        normalized["excited_states"] = [
            ExcitedStateSpec(**dict(spec))
            for spec in normalized.get("excited_states", [])
        ]
        materialized.append(StateMasterEntry(**normalized))
    return materialized


def materialize_state_master(
    entries: Sequence[StateMasterEntry],
    *,
    families: Optional[Iterable[str]] = None,
    charge_window_min: Optional[int] = None,
    charge_window_max: Optional[int] = None,
    include_disabled: bool = False,
    asd: Optional[NistAsdBootstrapAdapter] = None,
    asd_max_ion_charge: int = 0,
    asd_max_levels_per_spectrum: int = 0,
) -> List[SpeciesPrototype]:
    allowed_families = {item.lower() for item in families} if families else None
    prototypes: List[SpeciesPrototype] = []
    seen: set[str] = set()
    for entry in entries:
        if not include_disabled and not entry.enabled:
            continue
        if allowed_families is not None and entry.family.lower() not in allowed_families:
            continue
        for charge in _materialized_charges(
            entry,
            charge_window_min=charge_window_min,
            charge_window_max=charge_window_max,
        ):
            _append_if_new(
                prototypes,
                seen,
                _entry_to_species(entry, charge=charge),
            )
        for excited in _materialized_excited_species(
            entry,
            charge_window_min=charge_window_min,
            charge_window_max=charge_window_max,
        ):
            _append_if_new(prototypes, seen, excited)
        for source_backed in _materialized_atomic_asd_species(
            entry,
            charge_window_min=charge_window_min,
            charge_window_max=charge_window_max,
            asd=asd,
            asd_max_ion_charge=asd_max_ion_charge,
            asd_max_levels_per_spectrum=asd_max_levels_per_spectrum,
        ):
            _append_if_new(prototypes, seen, source_backed)
    prototypes.sort(key=lambda item: (item.formula, item.charge, item.key))
    return prototypes


def materialize_state_master_file(
    input_path: str | Path,
    *,
    output_path: str | Path,
    families: Optional[Iterable[str]] = None,
    charge_window_min: Optional[int] = None,
    charge_window_max: Optional[int] = None,
    include_disabled: bool = False,
    asd: Optional[NistAsdBootstrapAdapter] = None,
    asd_max_ion_charge: int = 0,
    asd_max_levels_per_spectrum: int = 0,
) -> Path:
    entries = load_state_master(input_path)
    prototypes = materialize_state_master(
        entries,
        families=families,
        charge_window_min=charge_window_min,
        charge_window_max=charge_window_max,
        include_disabled=include_disabled,
        asd=asd,
        asd_max_ion_charge=asd_max_ion_charge,
        asd_max_levels_per_spectrum=asd_max_levels_per_spectrum,
    )
    return write_species_catalog(output_path, prototypes)


def write_species_catalog(path: str | Path, prototypes: Sequence[SpeciesPrototype]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "species": [prototype.as_dict() for prototype in prototypes],
    }
    text = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
    target.write_text(text, encoding="utf-8")
    return target


def _materialized_charges(
    entry: StateMasterEntry,
    *,
    charge_window_min: Optional[int],
    charge_window_max: Optional[int],
) -> List[int]:
    charges = sorted(set(entry.allowed_charges or [0]))
    selected: List[int] = []
    for charge in charges:
        if charge < entry.charge_window_min or charge > entry.charge_window_max:
            continue
        if charge_window_min is not None and charge < charge_window_min:
            continue
        if charge_window_max is not None and charge > charge_window_max:
            continue
        selected.append(charge)
    return selected


def _entry_to_species(entry: StateMasterEntry, *, charge: int) -> SpeciesPrototype:
    neutral_state_class = parse_species_token(entry.preferred_key).state_class
    state_class = neutral_state_class
    if charge > 0:
        state_class = "cation"
    elif charge < 0:
        state_class = "anion"
    key = _charged_key(entry.preferred_key, charge)
    display_name = entry.display_name if charge == 0 else key
    aliases = list(entry.aliases) if charge == 0 else [_charged_key(alias, charge) for alias in entry.aliases]
    tags = _merge_tags(
        entry.tags,
        entry.family,
        "generated_from_state_master",
        "ion" if charge > 0 else "anion" if charge < 0 else state_class,
    )
    return SpeciesPrototype(
        key=key,
        display_name=display_name,
        formula=entry.formula,
        charge=charge,
        state_class=state_class,
        multiplicity=entry.multiplicity,
        structure_id=entry.structure_id,
        nist_query=entry.nist_query,
        aliases=aliases,
        tags=tags,
        metadata={
            "state_origin": "state_master",
            "state_family": entry.family,
            "state_master_species_id": entry.species_id,
        },
    )


def _materialized_excited_species(
    entry: StateMasterEntry,
    *,
    charge_window_min: Optional[int],
    charge_window_max: Optional[int],
) -> List[SpeciesPrototype]:
    prototypes: List[SpeciesPrototype] = []
    for spec in entry.excited_states:
        if not spec.enabled:
            continue
        if not _charge_within_window(
            spec.charge,
            entry=entry,
            charge_window_min=charge_window_min,
            charge_window_max=charge_window_max,
        ):
            continue
        base_key = _charged_key(entry.preferred_key, spec.charge)
        key = f"{base_key}[{spec.label}]"
        display_name = spec.display_name or f"{entry.display_name}({spec.label})"
        aliases = list(spec.aliases)
        if not aliases and entry.aliases:
            aliases = [f"{_charged_key(alias, spec.charge)}[{spec.label}]" for alias in entry.aliases]
        prototypes.append(
            SpeciesPrototype(
                key=key,
                display_name=display_name,
                formula=entry.formula,
                charge=spec.charge,
                state_class=spec.state_class,
                multiplicity=entry.multiplicity,
                structure_id=entry.structure_id,
                excitation_label=spec.label,
                excitation_energy_ev=spec.energy_ev,
                nist_query=entry.nist_query,
                aliases=aliases,
                tags=_merge_tags(
                    entry.tags,
                    entry.family,
                    spec.tags,
                    "generated_from_state_master",
                    spec.state_class,
                    "excited",
                ),
                metadata={
                    "state_origin": "state_master_excited",
                    "state_family": entry.family,
                    "state_master_species_id": entry.species_id,
                },
            )
        )
    return prototypes


def _materialized_atomic_asd_species(
    entry: StateMasterEntry,
    *,
    charge_window_min: Optional[int],
    charge_window_max: Optional[int],
    asd: Optional[NistAsdBootstrapAdapter],
    asd_max_ion_charge: int,
    asd_max_levels_per_spectrum: int,
) -> List[SpeciesPrototype]:
    if asd is None:
        return []
    if entry.excitation_policy != "atomic_asd":
        return []
    if not _is_atomic_formula(entry.formula):
        return []
    prototypes: List[SpeciesPrototype] = []
    for prototype in asd.bootstrap(
        [entry.formula],
        max_ion_charge=asd_max_ion_charge,
        max_levels_per_spectrum=asd_max_levels_per_spectrum,
    ):
        if prototype.formula != entry.formula:
            continue
        if prototype.charge not in set(entry.allowed_charges or [0]):
            continue
        if not _charge_within_window(
            prototype.charge,
            entry=entry,
            charge_window_min=charge_window_min,
            charge_window_max=charge_window_max,
        ):
            continue
        prototypes.append(
            SpeciesPrototype(
                key=prototype.key,
                display_name=prototype.display_name,
                formula=prototype.formula,
                charge=prototype.charge,
                state_class=prototype.state_class,
                multiplicity=entry.multiplicity,
                structure_id=entry.structure_id,
                excitation_label=prototype.excitation_label,
                excitation_energy_ev=prototype.excitation_energy_ev,
                nist_query=entry.nist_query,
                aliases=[],
                tags=_merge_tags(
                    entry.tags,
                    entry.family,
                    prototype.tags,
                    "generated_from_state_master",
                    "source_backed",
                ),
                metadata={
                    "state_origin": "state_master_atomic_asd",
                    "state_family": entry.family,
                    "state_master_species_id": entry.species_id,
                },
            )
        )
    return prototypes


def _charge_within_window(
    charge: int,
    *,
    entry: StateMasterEntry,
    charge_window_min: Optional[int],
    charge_window_max: Optional[int],
) -> bool:
    if charge < entry.charge_window_min or charge > entry.charge_window_max:
        return False
    if charge_window_min is not None and charge < charge_window_min:
        return False
    if charge_window_max is not None and charge > charge_window_max:
        return False
    return True


def _is_atomic_formula(formula: str) -> bool:
    try:
        composition = parse_formula(formula)
    except ValueError:
        return False
    return len(composition) == 1 and next(iter(composition.values())) == 1


def _append_if_new(prototypes: List[SpeciesPrototype], seen: set[str], prototype: SpeciesPrototype) -> None:
    if prototype.key in seen:
        return
    prototypes.append(prototype)
    seen.add(prototype.key)


def _charged_key(base: str, charge: int) -> str:
    if charge > 0:
        return base + ("+" * charge)
    if charge < 0:
        return base + ("-" * abs(charge))
    return base


def _merge_tags(*groups: str | Iterable[str]) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()
    for group in groups:
        if isinstance(group, str):
            candidates = [group]
        else:
            candidates = list(group)
        for candidate in candidates:
            if not candidate or candidate in seen:
                continue
            out.append(candidate)
            seen.add(candidate)
    return out
