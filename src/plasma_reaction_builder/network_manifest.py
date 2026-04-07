from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Sequence

from .model import BuildResult, ReactionRecord, SpeciesState


CURATED_TEMPLATE_ORIGINS = {"curated_catalog", "packaged_library"}
PROMOTED_TEMPLATE_ORIGINS = {
    "source_backed_promotion",
    "excited_state_template_generation",
    "external_seed",
}


def build_result_network_manifest(result: BuildResult) -> Dict[str, Any]:
    return _build_network_manifest(
        species=result.species,
        reactions=result.reactions,
        metadata=result.metadata,
    )


def build_network_manifest_from_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    return _build_network_manifest(
        species=list(payload.get("species", [])),
        reactions=list(payload.get("reactions", [])),
        metadata=dict(payload.get("metadata", {})),
    )


def _build_network_manifest(
    *,
    species: Sequence[SpeciesState | Dict[str, Any]],
    reactions: Sequence[ReactionRecord | Dict[str, Any]],
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    curated_reactions = [
        reaction
        for reaction in reactions
        if _reaction_origin(reaction) in CURATED_TEMPLATE_ORIGINS
    ]
    promoted_reactions = [
        reaction
        for reaction in reactions
        if _reaction_origin(reaction) in PROMOTED_TEMPLATE_ORIGINS
    ]
    return {
        "generated_at": _utc_now(),
        "config_sources": list(metadata.get("config_sources", [])),
        "catalog_policy": dict(metadata.get("catalog_policy", {})),
        "species_count": len(species),
        "reaction_count": len(reactions),
        "species_by_origin": _count_named_items(_species_origin(state) for state in species),
        "reaction_by_origin": _count_named_items(_reaction_origin(reaction) for reaction in reactions),
        "reaction_by_layer": _count_named_items(_reaction_metadata_value(reaction, "template_layer") for reaction in reactions),
        "reaction_by_family": _count_named_items(_reaction_family(reaction) for reaction in reactions),
        "reaction_template_source_systems": _count_named_items(
            _reaction_metadata_value(reaction, "template_source_system") for reaction in reactions
        ),
        "reaction_template_source_names": _count_named_items(
            _reaction_metadata_value(reaction, "template_source_name") for reaction in reactions
        ),
        "reaction_evidence_source_systems": _count_named_items(
            _iter_reaction_evidence_values(reactions, key="source_system")
        ),
        "reaction_evidence_source_names": _count_named_items(
            _iter_reaction_evidence_values(reactions, key="source_name")
        ),
        "reaction_catalog_resources": _count_named_items(
            _reaction_metadata_value(reaction, "catalog_resource") for reaction in reactions
        ),
        "fallback_usage": {
            "count": len(curated_reactions),
            "families": _count_named_items(_reaction_family(reaction) for reaction in curated_reactions),
            "catalog_resources": _count_named_items(
                _reaction_metadata_value(reaction, "catalog_resource") for reaction in curated_reactions
            ),
        },
        "promoted_usage": {
            "count": len(promoted_reactions),
            "origins": _count_named_items(_reaction_origin(reaction) for reaction in promoted_reactions),
            "template_source_systems": _count_named_items(
                _reaction_metadata_value(reaction, "template_source_system") for reaction in promoted_reactions
            ),
            "template_source_names": _count_named_items(
                _reaction_metadata_value(reaction, "template_source_name") for reaction in promoted_reactions
            ),
        },
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _species_origin(state: SpeciesState | Dict[str, Any]) -> str:
    metadata = _state_metadata(state)
    return str(metadata.get("state_origin") or "unknown")


def _reaction_origin(reaction: ReactionRecord | Dict[str, Any]) -> str:
    return str(_reaction_metadata_value(reaction, "template_origin") or "unknown")


def _reaction_family(reaction: ReactionRecord | Dict[str, Any]) -> str:
    if isinstance(reaction, dict):
        return str(reaction.get("family") or "unknown")
    return str(reaction.family or "unknown")


def _reaction_metadata_value(reaction: ReactionRecord | Dict[str, Any], key: str) -> str:
    metadata = _reaction_metadata(reaction)
    value = metadata.get(key)
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(item) for item in value if item)
    return str(value)


def _state_metadata(state: SpeciesState | Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(state, dict):
        return dict(state.get("metadata", {}))
    return dict(state.metadata)


def _reaction_metadata(reaction: ReactionRecord | Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(reaction, dict):
        return dict(reaction.get("metadata", {}))
    return dict(reaction.metadata)


def _iter_reaction_evidence_values(
    reactions: Iterable[ReactionRecord | Dict[str, Any]],
    *,
    key: str,
) -> Iterable[str]:
    for reaction in reactions:
        if isinstance(reaction, dict):
            evidence_items = list(reaction.get("evidence", []))
            for item in evidence_items:
                value = item.get(key)
                if value:
                    yield str(value)
            continue
        for item in reaction.evidence:
            value = getattr(item, key, None)
            if value:
                yield str(value)


def _count_named_items(values: Iterable[str]) -> List[Dict[str, Any]]:
    counts: Counter[str] = Counter()
    for value in values:
        if not value:
            continue
        counts[str(value)] += 1
    return [
        {"name": name, "count": counts[name]}
        for name in sorted(counts)
    ]
