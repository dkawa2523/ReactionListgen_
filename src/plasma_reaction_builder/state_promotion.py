from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .adapters.evidence_common import ReactionEvidenceEntry, ReactionEvidenceIndex
from .config import MolecularExcitedStatePromotionOptions
from .excited_state_registry import ExcitedStateRegistry
from .formula import parse_species_token
from .model import SpeciesPrototype
from .state_catalog import StateMasterEntry


PROMOTABLE_MOLECULAR_POLICIES = {"molecular_curated", "molecular_promoted", "bucket_only"}


@dataclass(slots=True)
class MolecularExcitedStateCandidate:
    base_species_key: str
    promoted_key: str
    display_name: str
    formula: str
    charge: int
    state_class: str
    excitation_label: Optional[str]
    excitation_energy_ev: Optional[float]
    support_score: float
    source_system: str
    source_name: str
    citation: Optional[str] = None
    source_url: Optional[str] = None
    note: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


def promote_molecular_excited_states(
    *,
    state_master_entries: Sequence[StateMasterEntry],
    indexes: Iterable[ReactionEvidenceIndex],
    existing_species: Dict[str, SpeciesPrototype],
    options: MolecularExcitedStatePromotionOptions,
    excited_state_registry: Optional[ExcitedStateRegistry] = None,
) -> List[SpeciesPrototype]:
    if not options.enabled:
        return []
    eligible_entries = [
        entry
        for entry in state_master_entries
        if entry.excitation_policy in PROMOTABLE_MOLECULAR_POLICIES
        and len(entry.formula) > 1
    ]
    if not eligible_entries:
        return []

    allowed_sources = {item.lower() for item in options.source_systems}
    per_base: Dict[str, List[MolecularExcitedStateCandidate]] = defaultdict(list)
    for index in indexes:
        for evidence_entry in index.entries:
            if evidence_entry.source_system.lower() not in allowed_sources:
                continue
            if evidence_entry.support_score < options.min_support_score:
                continue
            if not _has_electron_signal(evidence_entry, require_signal=options.require_electron_signal):
                continue
            for state_entry in eligible_entries:
                if not _entry_matches_base_species(evidence_entry, state_entry):
                    continue
                per_base[state_entry.preferred_key].extend(
                    _extract_candidates_from_entry(
                        evidence_entry,
                        state_entry=state_entry,
                        excited_state_registry=excited_state_registry or ExcitedStateRegistry.empty(),
                    )
                )

    prototypes: List[SpeciesPrototype] = []
    for state_entry in eligible_entries:
        ranked = _dedupe_candidates(per_base.get(state_entry.preferred_key, []))
        for candidate in ranked[: max(0, options.max_states_per_species)]:
            if candidate.promoted_key in existing_species:
                continue
            prototypes.append(
                SpeciesPrototype(
                    key=candidate.promoted_key,
                    display_name=candidate.display_name,
                    formula=candidate.formula,
                    charge=candidate.charge,
                    state_class=candidate.state_class,
                    multiplicity=state_entry.multiplicity,
                    structure_id=state_entry.structure_id,
                    excitation_label=candidate.excitation_label,
                    excitation_energy_ev=candidate.excitation_energy_ev,
                    nist_query=state_entry.nist_query,
                    aliases=[],
                    tags=_merge_tags(
                        state_entry.tags,
                        state_entry.family,
                        "promoted_excited_state",
                        "source_backed",
                        "molecular_excited",
                        candidate.source_system,
                    ),
                    metadata={
                        "state_origin": "source_backed_state_promotion",
                        "promotion_kind": "molecular_excited_state",
                        "base_species_key": state_entry.preferred_key,
                        "source_system": candidate.source_system,
                        "source_name": candidate.source_name,
                        "support_score": candidate.support_score,
                        "citation": candidate.citation,
                        "source_url": candidate.source_url,
                        "note": candidate.note,
                        **candidate.metadata,
                    },
                )
            )
    return prototypes


def _has_electron_signal(entry: ReactionEvidenceEntry, *, require_signal: bool) -> bool:
    if not require_signal:
        return True
    if any(parse_species_token(token).normalized_label == "e-" for token in entry.reactants):
        return True
    metadata = " ".join(str(value) for value in entry.metadata.values() if value is not None).lower()
    note = (entry.note or "").lower()
    citation = (entry.citation or "").lower()
    evidence_kind = (entry.evidence_kind or "").lower()
    return any(
        needle in " ".join([metadata, note, citation, evidence_kind])
        for needle in ("electron", "excitation", "vibrational", "electronic")
    )


def _entry_matches_base_species(entry: ReactionEvidenceEntry, state_entry: StateMasterEntry) -> bool:
    accepted = {state_entry.preferred_key, state_entry.formula, *state_entry.aliases}
    reactant_tokens = set()
    for token in entry.reactants:
        parsed = parse_species_token(token)
        if not parsed.tracked:
            continue
        reactant_tokens.add(parsed.normalized_label)
        if parsed.formula:
            reactant_tokens.add(parsed.formula)
    return bool(accepted.intersection(reactant_tokens))


def _extract_candidates_from_entry(
    entry: ReactionEvidenceEntry,
    *,
    state_entry: StateMasterEntry,
    excited_state_registry: ExcitedStateRegistry,
) -> List[MolecularExcitedStateCandidate]:
    candidates: List[MolecularExcitedStateCandidate] = []
    candidates.extend(
        _explicit_product_candidates(
            entry,
            state_entry=state_entry,
            excited_state_registry=excited_state_registry,
        )
    )
    candidates.extend(
        _metadata_candidates(
            entry,
            state_entry=state_entry,
            excited_state_registry=excited_state_registry,
        )
    )
    return candidates


def _explicit_product_candidates(
    entry: ReactionEvidenceEntry,
    *,
    state_entry: StateMasterEntry,
    excited_state_registry: ExcitedStateRegistry,
) -> List[MolecularExcitedStateCandidate]:
    candidates: List[MolecularExcitedStateCandidate] = []
    for token in entry.products:
        parsed = parse_species_token(token)
        if not parsed.tracked:
            continue
        if parsed.formula != state_entry.formula:
            continue
        if parsed.charge not in set(state_entry.allowed_charges or [0]):
            continue
        if not (parsed.excitation_label or parsed.state_class == "excited_bucket"):
            continue
        display_name = token.strip()
        if parsed.excitation_label:
            display_name = f"{state_entry.display_name}({parsed.excitation_label})"
        promoted_key, canonical_label, canonical_energy_ev, registry_entry = _canonicalize_candidate(
            token=token,
            source_system=entry.source_system,
            base_species_key=state_entry.preferred_key,
            excitation_energy_ev=parsed.excitation_energy_ev,
            fallback_key=parsed.normalized_label,
            fallback_label=parsed.excitation_label,
            fallback_energy_ev=parsed.excitation_energy_ev,
            excited_state_registry=excited_state_registry,
        )
        if canonical_label:
            display_name = f"{state_entry.display_name}({canonical_label})"
        candidates.append(
            MolecularExcitedStateCandidate(
                base_species_key=state_entry.preferred_key,
                promoted_key=promoted_key,
                display_name=display_name,
                formula=state_entry.formula,
                charge=parsed.charge,
                state_class=parsed.state_class,
                excitation_label=canonical_label,
                excitation_energy_ev=canonical_energy_ev,
                support_score=entry.support_score,
                source_system=entry.source_system,
                source_name=entry.source_name,
                citation=entry.citation,
                source_url=entry.source_url,
                note=entry.note,
                metadata={
                    "promotion_origin": "explicit_product",
                    **_registry_metadata(registry_entry),
                },
            )
        )
    return candidates


def _metadata_candidates(
    entry: ReactionEvidenceEntry,
    *,
    state_entry: StateMasterEntry,
    excited_state_registry: ExcitedStateRegistry,
) -> List[MolecularExcitedStateCandidate]:
    raw_specs = entry.metadata.get("promoted_excited_states", [])
    if isinstance(raw_specs, dict):
        raw_specs = [raw_specs]
    if not isinstance(raw_specs, list):
        return []
    candidates: List[MolecularExcitedStateCandidate] = []
    for raw in raw_specs:
        if not isinstance(raw, dict):
            continue
        token = str(raw.get("token") or "").strip()
        label = raw.get("label")
        if token:
            parsed = parse_species_token(token)
            charge = parsed.charge
            state_class = parsed.state_class
            formula = parsed.formula or state_entry.formula
            promoted_key, excitation_label, excitation_energy_ev, registry_entry = _canonicalize_candidate(
                token=token,
                source_system=entry.source_system,
                base_species_key=state_entry.preferred_key,
                excitation_energy_ev=(
                    float(raw["energy_ev"])
                    if raw.get("energy_ev") is not None
                    else parsed.excitation_energy_ev
                ),
                fallback_key=parsed.normalized_label,
                fallback_label=parsed.excitation_label or (str(label) if label else None),
                fallback_energy_ev=parsed.excitation_energy_ev,
                excited_state_registry=excited_state_registry,
            )
        else:
            excitation_label = str(label) if label else None
            if not excitation_label:
                continue
            charge = int(raw.get("charge", 0))
            registry_entry = excited_state_registry.lookup_label(
                base_species_key=state_entry.preferred_key,
                charge=charge,
                label=excitation_label,
                source_system=entry.source_system,
                excitation_energy_ev=(
                    float(raw["energy_ev"])
                    if raw.get("energy_ev") is not None
                    else None
                ),
            )
            if registry_entry is not None:
                canonical = parse_species_token(registry_entry.canonical_key)
                promoted_key = registry_entry.canonical_key
                excitation_label = canonical.excitation_label or excitation_label
                excitation_energy_ev = (
                    registry_entry.excitation_energy_ev
                    if registry_entry.excitation_energy_ev is not None
                    else (
                        float(raw["energy_ev"])
                        if raw.get("energy_ev") is not None
                        else None
                    )
                )
            else:
                promoted_key = f"{state_entry.preferred_key}[{excitation_label}]"
                excitation_energy_ev = (
                    float(raw["energy_ev"])
                    if raw.get("energy_ev") is not None
                    else None
                )
            state_class = str(raw.get("state_class") or "excited")
            formula = state_entry.formula
        if formula != state_entry.formula:
            continue
        if charge not in set(state_entry.allowed_charges or [0]):
            continue
        candidates.append(
            MolecularExcitedStateCandidate(
                base_species_key=state_entry.preferred_key,
                promoted_key=promoted_key,
                display_name=str(raw.get("display_name") or f"{state_entry.display_name}({excitation_label})"),
                formula=formula,
                charge=charge,
                state_class=state_class,
                excitation_label=excitation_label,
                excitation_energy_ev=(
                    float(raw["energy_ev"])
                    if raw.get("energy_ev") is not None
                    else excitation_energy_ev
                ),
                support_score=entry.support_score,
                source_system=entry.source_system,
                source_name=entry.source_name,
                citation=entry.citation,
                source_url=entry.source_url,
                note=entry.note,
                metadata={
                    "promotion_origin": "metadata",
                    **_registry_metadata(registry_entry),
                    **{key: value for key, value in raw.items() if key not in {"display_name"}},
                },
            )
        )
    return candidates


def _dedupe_candidates(candidates: Sequence[MolecularExcitedStateCandidate]) -> List[MolecularExcitedStateCandidate]:
    best: Dict[str, MolecularExcitedStateCandidate] = {}
    for candidate in candidates:
        current = best.get(candidate.promoted_key)
        if current is None or _candidate_sort_key(candidate) > _candidate_sort_key(current):
            best[candidate.promoted_key] = candidate
    return sorted(best.values(), key=_candidate_sort_key, reverse=True)


def _candidate_sort_key(candidate: MolecularExcitedStateCandidate) -> tuple[float, float, float, str]:
    energy = candidate.excitation_energy_ev if candidate.excitation_energy_ev is not None else -1.0
    priority_match = 1.0 if candidate.metadata.get("registry_priority_source") == candidate.source_system else 0.0
    return (priority_match, candidate.support_score, -energy, candidate.promoted_key)


def _merge_tags(*groups: Iterable[str] | str) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()
    for group in groups:
        if isinstance(group, str):
            items = [group]
        else:
            items = list(group)
        for item in items:
            if not item or item in seen:
                continue
            out.append(item)
            seen.add(item)
    return out


def _canonicalize_candidate(
    *,
    token: str,
    source_system: str,
    base_species_key: str,
    excitation_energy_ev: Optional[float],
    fallback_key: str,
    fallback_label: Optional[str],
    fallback_energy_ev: Optional[float],
    excited_state_registry: ExcitedStateRegistry,
) -> tuple[str, Optional[str], Optional[float], Optional[object]]:
    registry_entry = excited_state_registry.lookup(
        token,
        source_system=source_system,
        base_species_key=base_species_key,
        excitation_energy_ev=excitation_energy_ev,
    )
    if registry_entry is None and fallback_label:
        registry_entry = excited_state_registry.lookup_label(
            base_species_key=base_species_key,
            charge=parse_species_token(fallback_key).charge,
            label=fallback_label,
            source_system=source_system,
            excitation_energy_ev=excitation_energy_ev,
        )
    if registry_entry is None:
        fallback_energy = excitation_energy_ev if excitation_energy_ev is not None else fallback_energy_ev
        return fallback_key, fallback_label, fallback_energy, None
    canonical = parse_species_token(registry_entry.canonical_key)
    return (
        registry_entry.canonical_key,
        canonical.excitation_label or fallback_label,
        registry_entry.excitation_energy_ev if registry_entry.excitation_energy_ev is not None else (excitation_energy_ev or fallback_energy_ev),
        registry_entry,
    )


def _registry_metadata(registry_entry: Optional[object]) -> Dict[str, Any]:
    if registry_entry is None:
        return {}
    canonical_key = getattr(registry_entry, "canonical_key", None)
    priority_source = getattr(registry_entry, "priority_source", None)
    energy_tolerance_ev = getattr(registry_entry, "energy_tolerance_ev", None)
    return {
        "registry_canonical_key": canonical_key,
        "registry_priority_source": priority_source,
        "registry_energy_tolerance_ev": energy_tolerance_ev,
    }
