from __future__ import annotations

from collections import defaultdict
from hashlib import sha1
from typing import Dict, Iterable, List, Optional, Sequence, Set

from .adapters.evidence_common import ReactionEvidenceEntry, ReactionEvidenceIndex, evidence_entry_to_template
from .catalog import DEFAULT_PROMOTED_TEMPLATE_PRIORITY
from .config import SourceBackedTemplatePromotionOptions
from .formula import parse_species_token
from .model import ReactionTemplate, SpeciesPrototype
from .state_catalog import StateMasterEntry


REACTION_FAMILY_ALIASES = {
    "attachment": "electron_attachment",
    "charge-transfer": "charge_transfer",
    "charge_transfer": "charge_transfer",
    "dissociation": "electron_dissociation",
    "dissociative_recombination": "dissociative_recombination",
    "electron_attachment": "electron_attachment",
    "electron_dissociation": "electron_dissociation",
    "electron_impact_attachment": "electron_attachment",
    "electron_impact_dissociation": "electron_dissociation",
    "electron_impact_ionization": "electron_ionization",
    "electron_ionization": "electron_ionization",
    "electron_recombination": "dissociative_recombination",
    "ion_neutral_followup": "ion_neutral_followup",
    "ionization": "electron_ionization",
    "mutual-neutralisation": "mutual_neutralization",
    "mutual-neutralization": "mutual_neutralization",
    "mutual_neutralisation": "mutual_neutralization",
    "mutual_neutralization": "mutual_neutralization",
    "radical_neutral": "radical_neutral_reaction",
    "radical_neutral_reaction": "radical_neutral_reaction",
    "recombination": "dissociative_recombination",
}

TARGET_FAMILY_METADATA_KEYS = (
    "promotion_family",
    "curated_family",
    "chemistry_family",
)

REACTION_FAMILY_METADATA_KEYS = (
    "promotion_reaction_family",
    "curated_reaction_family",
    "process_family",
    "reaction_family",
)


def promote_source_backed_templates(
    *,
    state_master_entries: Sequence[StateMasterEntry],
    indexes: Iterable[ReactionEvidenceIndex],
    existing_species: Dict[str, SpeciesPrototype],
    existing_templates: Sequence[ReactionTemplate],
    options: SourceBackedTemplatePromotionOptions,
) -> List[ReactionTemplate]:
    if not options.enabled:
        return []

    allowed_sources = {item.lower() for item in options.source_systems}
    allowed_reaction_families = {_canonical_reaction_family(item) for item in options.allowed_reaction_families}
    target_family_tokens = _target_family_tokens(state_master_entries, configured_families=options.target_families)
    if not target_family_tokens:
        return []

    known_species = set(existing_species)
    existing_equations = {template.equation() for template in existing_templates}
    grouped: Dict[str, List[tuple[float, ReactionTemplate]]] = defaultdict(list)

    for index in indexes:
        for entry in index.entries:
            if entry.source_system.lower() not in allowed_sources:
                continue
            if entry.support_score < options.min_support_score:
                continue
            target_family = _resolve_target_family(entry, target_family_tokens)
            if not target_family:
                continue
            reaction_family = _resolve_reaction_family(entry)
            if not reaction_family or reaction_family not in allowed_reaction_families:
                continue
            template = evidence_entry_to_template(entry)
            if template is None:
                continue
            if options.require_catalog_species and not _catalog_supports_entry(entry, known_species):
                continue
            if template.equation() in existing_equations:
                continue
            promoted = _promoted_template(
                template,
                entry=entry,
                target_family=target_family,
                reaction_family=reaction_family,
            )
            grouped[target_family].append((entry.support_score, promoted))

    promoted_templates: List[ReactionTemplate] = []
    for family in sorted(grouped):
        ranked = sorted(
            grouped[family],
            key=lambda item: (-item[0], item[1].equation(), item[1].key),
        )
        count = 0
        for _, template in ranked:
            if count >= options.max_templates_per_family:
                break
            if template.equation() in existing_equations:
                continue
            promoted_templates.append(template)
            existing_equations.add(template.equation())
            count += 1
    return promoted_templates


def _target_family_tokens(
    entries: Sequence[StateMasterEntry],
    *,
    configured_families: Sequence[str],
) -> Dict[str, Set[str]]:
    requested = {item.lower() for item in configured_families if item}
    include_all = not requested
    tokens_by_family: Dict[str, Set[str]] = defaultdict(set)
    for entry in entries:
        family = entry.family.lower()
        if not include_all and family not in requested:
            continue
        tokens_by_family[family].update(_tracked_variants(entry.preferred_key))
        tokens_by_family[family].update(_tracked_variants(entry.formula))
        for alias in entry.aliases:
            tokens_by_family[family].update(_tracked_variants(alias))
    return dict(tokens_by_family)


def _tracked_variants(token: str) -> Set[str]:
    parsed = parse_species_token(token)
    out: Set[str] = set()
    if parsed.tracked:
        out.add(parsed.normalized_label)
        if parsed.formula:
            out.add(parsed.formula)
    elif token:
        out.add(token)
    return out


def _resolve_target_family(
    entry: ReactionEvidenceEntry,
    target_family_tokens: Dict[str, Set[str]],
) -> Optional[str]:
    hinted_family = _metadata_family(entry)
    if hinted_family and hinted_family in target_family_tokens:
        return hinted_family
    matched = []
    overlap = _entry_overlap_tokens(entry)
    for family, accepted_tokens in target_family_tokens.items():
        if overlap.intersection(accepted_tokens):
            matched.append(family)
    if len(matched) == 1:
        return matched[0]
    return None


def _metadata_family(entry: ReactionEvidenceEntry) -> Optional[str]:
    for key in TARGET_FAMILY_METADATA_KEYS:
        value = entry.metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
    return None


def _resolve_reaction_family(entry: ReactionEvidenceEntry) -> Optional[str]:
    for key in REACTION_FAMILY_METADATA_KEYS:
        value = entry.metadata.get(key)
        if isinstance(value, str) and value.strip():
            return _canonical_reaction_family(value)
    return None


def _canonical_reaction_family(value: str) -> str:
    normalized = value.strip().lower().replace(" ", "_")
    return REACTION_FAMILY_ALIASES.get(normalized, normalized)


def _entry_overlap_tokens(entry: ReactionEvidenceEntry) -> Set[str]:
    out: Set[str] = set()
    for token in list(entry.reactants) + list(entry.products):
        parsed = parse_species_token(token)
        if not parsed.tracked:
            continue
        out.add(parsed.normalized_label)
        if parsed.formula:
            out.add(parsed.formula)
    return out


def _catalog_supports_entry(entry: ReactionEvidenceEntry, known_species: Set[str]) -> bool:
    for token in list(entry.reactants) + list(entry.products):
        parsed = parse_species_token(token)
        if not parsed.tracked:
            continue
        if parsed.normalized_label not in known_species:
            return False
    return True


def _promoted_template(
    template: ReactionTemplate,
    *,
    entry: ReactionEvidenceEntry,
    target_family: str,
    reaction_family: str,
) -> ReactionTemplate:
    equation = template.equation()
    key_material = f"{target_family}|{reaction_family}|{entry.source_system}|{equation}"
    stage = str(entry.metadata.get("promotion_stage") or "source_backed_curated_bridge")
    note = (
        f"Source-backed template promotion for {target_family} family from {entry.source_name} "
        f"({stage})."
    )
    if entry.note:
        note += f" {entry.note}"
    return ReactionTemplate(
        key=f"promo::{target_family}::{entry.source_system}::{sha1(key_material.encode('utf-8')).hexdigest()[:16]}",
        reactants=list(template.reactants),
        products=list(template.products),
        lhs_tokens=list(template.lhs_tokens),
        rhs_tokens=list(template.rhs_tokens),
        family=reaction_family,
        required_projectile=template.required_projectile,
        threshold_ev=template.threshold_ev,
        delta_h_kj_mol=template.delta_h_kj_mol,
        base_confidence=max(template.base_confidence, min(0.92, entry.support_score)),
        evidence=list(template.evidence),
        reference_ids=[],
        note=note,
        inferred_balance=template.inferred_balance,
        missing_products=list(template.missing_products),
        metadata={
            **dict(template.metadata),
            "template_origin": "source_backed_promotion",
            "template_layer": "promotion",
            "template_priority": DEFAULT_PROMOTED_TEMPLATE_PRIORITY,
            "template_source_system": entry.source_system,
            "template_source_name": entry.source_name,
            "source_support_score": entry.support_score,
            "source_url": entry.source_url,
            "promotion_stage": stage,
            "promotion_target_family": target_family,
            "promotion_reaction_family": reaction_family,
        },
    )
