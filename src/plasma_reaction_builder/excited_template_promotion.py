from __future__ import annotations

from hashlib import sha1
from typing import Dict, Iterable, List, Optional, Sequence, Set

from .catalog import DEFAULT_EXCITED_TEMPLATE_PRIORITY
from .config import MolecularExcitedStateTemplatePromotionOptions
from .model import ReactionTemplate, SpeciesPrototype
from .provenance import EvidenceRecord
from .state_catalog import StateMasterEntry


DEFAULT_QUENCHING_PARTNERS = {
    "hydrocarbon": ["CH4", "H2"],
    "oxygen": ["O2", "N2"],
    "nitrogen": ["N2", "O2"],
    "fluorocarbon": ["c-C4F8", "CF4"],
    "boron": ["BCl3", "O2"],
    "chlorine": ["Cl2", "HCl"],
    "bromine": ["Br2", "HBr"],
    "silicon": ["SiH2Cl2", "SiHCl3", "H2"],
    "sulfur": ["SF6", "O2"],
    "tungsten": ["WF6", "H2"],
    "organosilicon": ["C8H20O4Si", "O2", "H2"],
    "noble_gas": ["Ar", "He"],
}


def promote_molecular_excited_state_templates(
    *,
    state_master_entries: Sequence[StateMasterEntry],
    existing_species: Dict[str, SpeciesPrototype],
    existing_templates: Sequence[ReactionTemplate],
    options: MolecularExcitedStateTemplatePromotionOptions,
) -> List[ReactionTemplate]:
    if not options.enabled:
        return []

    allowed_sources = {item.lower() for item in options.source_systems}
    target_families = {item.lower() for item in options.target_families if item}
    family_by_key = {
        entry.preferred_key: entry.family.lower()
        for entry in state_master_entries
    }
    existing_equations = {template.equation() for template in existing_templates}
    promoted: List[ReactionTemplate] = []

    for proto in existing_species.values():
        candidate = _candidate_from_species(
            proto,
            family_by_key=family_by_key,
            allowed_sources=allowed_sources,
            target_families=target_families,
            min_support_score=options.min_support_score,
            existing_species=existing_species,
        )
        if candidate is None:
            continue
        family, base_key, evidence = candidate
        excited_label = proto.excitation_label
        rhs_token = _display_excited_token(base_key, excited_label, proto.display_name)

        if options.include_electron_excitation:
            excitation_family = _excitation_family(excited_label)
            template = ReactionTemplate(
                key=_promotion_key("excitation", family, proto.key, excitation_family),
                reactants=[base_key],
                products=[proto.key],
                lhs_tokens=["e-", base_key],
                rhs_tokens=["e-", rhs_token],
                family=excitation_family,
                required_projectile="e-",
                threshold_ev=proto.excitation_energy_ev,
                base_confidence=max(0.72, min(0.94, evidence.support_score)),
                evidence=[evidence],
                note=f"Auto-generated from promoted molecular excited state {proto.key}.",
                metadata=_template_metadata(
                    proto,
                    evidence=evidence,
                    family=family,
                    reaction_family=excitation_family,
                    generation_kind="excitation",
                ),
            )
            if template.equation() not in existing_equations:
                promoted.append(template)
                existing_equations.add(template.equation())

        if options.include_radiative_relaxation:
            template = ReactionTemplate(
                key=_promotion_key("relaxation", family, proto.key, "radiative_relaxation"),
                reactants=[proto.key],
                products=[base_key],
                lhs_tokens=[rhs_token],
                rhs_tokens=[base_key],
                family="radiative_relaxation",
                base_confidence=max(0.64, min(0.90, evidence.support_score - 0.05)),
                evidence=[evidence],
                note=f"Auto-generated radiative relaxation channel for promoted molecular excited state {proto.key}.",
                metadata=_template_metadata(
                    proto,
                    evidence=evidence,
                    family=family,
                    reaction_family="radiative_relaxation",
                    generation_kind="relaxation",
                ),
            )
            if template.equation() not in existing_equations:
                promoted.append(template)
                existing_equations.add(template.equation())

        if options.include_collisional_quenching:
            for partner in _quenching_partners(
                family,
                existing_species=existing_species,
                configured_partners=options.quenching_partners,
            ):
                template = ReactionTemplate(
                    key=_promotion_key("quenching", family, f"{proto.key}|{partner}", "collisional_quenching"),
                    reactants=[proto.key, partner],
                    products=[base_key, partner],
                    lhs_tokens=[rhs_token, partner],
                    rhs_tokens=[base_key, partner],
                    family="collisional_quenching",
                    base_confidence=max(0.60, min(0.88, evidence.support_score - 0.06)),
                    evidence=[evidence],
                    note=(
                        f"Auto-generated collisional quenching channel for promoted molecular excited state "
                        f"{proto.key} with {partner}."
                    ),
                    metadata=_template_metadata(
                        proto,
                        evidence=evidence,
                        family=family,
                        reaction_family="collisional_quenching",
                        generation_kind="quenching",
                        partner=partner,
                    ),
                )
                if template.equation() not in existing_equations:
                    promoted.append(template)
                    existing_equations.add(template.equation())

        if options.include_superelastic_deexcitation:
            template = ReactionTemplate(
                key=_promotion_key("superelastic", family, proto.key, "superelastic_deexcitation"),
                reactants=[proto.key],
                products=[base_key],
                lhs_tokens=["e-", rhs_token],
                rhs_tokens=["e-", base_key],
                family="superelastic_deexcitation",
                required_projectile="e-",
                base_confidence=max(0.62, min(0.88, evidence.support_score - 0.07)),
                evidence=[evidence],
                note=f"Auto-generated superelastic de-excitation channel for promoted molecular excited state {proto.key}.",
                metadata=_template_metadata(
                    proto,
                    evidence=evidence,
                    family=family,
                    reaction_family="superelastic_deexcitation",
                    generation_kind="superelastic",
                ),
            )
            if template.equation() not in existing_equations:
                promoted.append(template)
                existing_equations.add(template.equation())

    return promoted


def _candidate_from_species(
    proto: SpeciesPrototype,
    *,
    family_by_key: Dict[str, str],
    allowed_sources: Set[str],
    target_families: Set[str],
    min_support_score: float,
    existing_species: Dict[str, SpeciesPrototype],
) -> Optional[tuple[str, str, EvidenceRecord]]:
    if not (proto.excitation_label or proto.state_class == "excited"):
        return None
    if proto.metadata.get("promotion_kind") != "molecular_excited_state":
        return None
    base_key = str(proto.metadata.get("base_species_key") or "").strip()
    if not base_key:
        base_key = proto.key.rsplit("[", 1)[0]
    if base_key not in existing_species:
        return None
    family = family_by_key.get(base_key) or _family_from_tags(proto.tags)
    if not family:
        return None
    if target_families and family not in target_families:
        return None
    source_system = str(proto.metadata.get("source_system") or "").lower()
    support_score = float(proto.metadata.get("support_score") or 0.0)
    if source_system not in allowed_sources:
        return None
    if support_score < min_support_score:
        return None
    return (
        family,
        base_key,
        EvidenceRecord(
            source_system=source_system,
            source_name=str(proto.metadata.get("source_name") or source_system),
            acquisition_method="promoted_species_template_generation",
            evidence_kind="promoted_excited_state_template",
            support_score=support_score,
            source_url=proto.metadata.get("source_url"),
            locator=proto.key,
            citation=proto.metadata.get("citation"),
            note=proto.metadata.get("note") or "Generated from promoted molecular excited state.",
        ),
    )


def _family_from_tags(tags: Iterable[str]) -> Optional[str]:
    ignored = {
        "generated_from_state_master",
        "promoted_excited_state",
        "source_backed",
        "molecular_excited",
        "metastable",
        "vibrational",
        "feed_candidate",
        "core",
    }
    for tag in tags:
        lowered = str(tag).lower()
        if lowered in ignored:
            continue
        return lowered
    return None


def _excitation_family(label: Optional[str]) -> str:
    text = str(label or "").strip().lower()
    if text.startswith("v"):
        return "electron_excitation_vibrational"
    return "electron_excitation"


def _display_excited_token(base_key: str, excitation_label: Optional[str], display_name: str) -> str:
    if excitation_label:
        return f"{base_key}({excitation_label})"
    return display_name or base_key


def _promotion_key(kind: str, family: str, species_key: str, reaction_family: str) -> str:
    material = f"{kind}|{family}|{species_key}|{reaction_family}"
    digest = sha1(material.encode("utf-8")).hexdigest()[:16]
    return f"promo_excited::{family}::{kind}::{digest}"


def _quenching_partners(
    family: str,
    *,
    existing_species: Dict[str, SpeciesPrototype],
    configured_partners: Dict[str, List[str]],
) -> List[str]:
    configured = configured_partners.get(family) or configured_partners.get(family.lower()) or []
    candidates = configured or DEFAULT_QUENCHING_PARTNERS.get(family.lower(), [])
    out: List[str] = []
    seen: Set[str] = set()
    for partner in candidates:
        if partner not in existing_species:
            continue
        if partner in seen:
            continue
        out.append(partner)
        seen.add(partner)
    return out


def _template_metadata(
    proto: SpeciesPrototype,
    *,
    evidence: EvidenceRecord,
    family: str,
    reaction_family: str,
    generation_kind: str,
    partner: Optional[str] = None,
) -> Dict[str, object]:
    metadata = {
        "template_origin": "excited_state_template_generation",
        "template_layer": "promotion",
        "template_priority": DEFAULT_EXCITED_TEMPLATE_PRIORITY,
        "template_source_system": evidence.source_system,
        "template_source_name": evidence.source_name,
        "source_support_score": evidence.support_score,
        "source_url": evidence.source_url,
        "promotion_target_family": family,
        "promotion_reaction_family": reaction_family,
        "generation_kind": generation_kind,
        "promoted_state_key": proto.key,
        "base_species_key": proto.metadata.get("base_species_key"),
    }
    if partner:
        metadata["quenching_partner"] = partner
    return metadata
