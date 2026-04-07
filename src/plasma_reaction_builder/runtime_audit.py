from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List

from .catalog import TemplateCatalog
from .runtime import AppRuntime
from .source_ops import build_catalog_manifest, build_evidence_manifest, inspect_sources


PROMOTED_TEMPLATE_ORIGINS = {
    "source_backed_promotion",
    "excited_state_template_generation",
    "external_seed",
}
PROMOTED_STATE_ORIGINS = {"source_backed_state_promotion"}


def build_runtime_audit(
    runtime: AppRuntime,
    *,
    head_vamdc: bool = False,
) -> Dict[str, Any]:
    inspection = inspect_sources(
        runtime.config,
        head_vamdc=head_vamdc,
        alias_resolver=runtime.alias_resolver,
        strength_registry=runtime.strength_registry,
    )
    catalog_manifest = build_catalog_manifest(
        runtime.catalog,
        config_path=runtime.config.config_path,
        reaction_conflict_policy=runtime.config.catalog_policy.reaction_conflict_policy,
    )
    source_manifest = build_evidence_manifest(runtime.indexes, config_path=runtime.config.config_path)
    fallback_catalogs = _catalog_inputs(runtime.config.catalog_paths, kind="fallback")
    reference_catalogs = _catalog_inputs(runtime.config.catalog_paths, kind="reference")
    source_readiness = _source_readiness(inspection)
    return {
        "config_path": runtime.config.config_path,
        "config_sources": list(runtime.config.config_sources),
        "feeds": [feed.as_dict() for feed in runtime.config.feeds],
        "projectiles": list(runtime.config.projectiles),
        "catalog_policy": runtime.config.catalog_policy.as_dict(),
        "catalog_inputs": {
            "libraries": list(runtime.config.libraries),
            "catalog_paths": list(runtime.config.catalog_paths),
            "state_masters": [spec.as_dict() for spec in runtime.config.state_masters],
        },
        "reference_catalogs": reference_catalogs,
        "fallback_catalogs": fallback_catalogs,
        "loaded_resources": list(runtime.catalog.loaded_resources),
        "promotion_summary": {
            "source_backed_templates": {
                **runtime.config.template_promotions.source_backed_templates.as_dict(),
                "configured_sources": _configured_sources(
                    runtime,
                    enabled=runtime.config.template_promotions.source_backed_templates.enabled,
                    allowed_source_systems=runtime.config.template_promotions.source_backed_templates.source_systems,
                ),
                "promoted_template_count": _count_named_items(
                    catalog_manifest.get("templates_by_origin", []),
                    allowed_names=PROMOTED_TEMPLATE_ORIGINS,
                ),
                "template_source_systems": _catalog_template_metadata_counts(
                    runtime.catalog,
                    origins={"source_backed_promotion"},
                    key="template_source_system",
                ),
                "template_source_names": _catalog_template_metadata_counts(
                    runtime.catalog,
                    origins={"source_backed_promotion"},
                    key="template_source_name",
                ),
            },
            "molecular_excited_states": {
                **runtime.config.state_promotions.molecular_excited_states.as_dict(),
                "configured_sources": _configured_sources(
                    runtime,
                    enabled=runtime.config.state_promotions.molecular_excited_states.enabled,
                    allowed_source_systems=runtime.config.state_promotions.molecular_excited_states.source_systems,
                ),
                "promoted_species_count": _count_named_items(
                    catalog_manifest.get("species_by_origin", []),
                    allowed_names=PROMOTED_STATE_ORIGINS,
                ),
            },
            "molecular_excited_state_templates": {
                **runtime.config.template_promotions.molecular_excited_state_templates.as_dict(),
                "configured_sources": _configured_sources(
                    runtime,
                    enabled=runtime.config.template_promotions.molecular_excited_state_templates.enabled,
                    allowed_source_systems=runtime.config.template_promotions.molecular_excited_state_templates.source_systems,
                ),
                "promoted_template_count": _count_named_items(
                    catalog_manifest.get("templates_by_origin", []),
                    allowed_names={"excited_state_template_generation"},
                ),
            },
        },
        "source_readiness": source_readiness,
        "source_manifest": source_manifest,
        "catalog_manifest": catalog_manifest,
        "summary": {
            "build_ready": bool(inspection.get("summary", {}).get("build_ready")),
            "bootstrap_ready": bool(inspection.get("summary", {}).get("bootstrap_ready")),
            "reaction_evidence_required": bool(inspection.get("summary", {}).get("reaction_evidence_required")),
            "configured_source_count": len(source_readiness),
            "fallback_catalog_count": len(fallback_catalogs),
            "promoted_template_count": _count_named_items(
                catalog_manifest.get("templates_by_origin", []),
                allowed_names=PROMOTED_TEMPLATE_ORIGINS,
            ),
            "promoted_species_count": _count_named_items(
                catalog_manifest.get("species_by_origin", []),
                allowed_names=PROMOTED_STATE_ORIGINS,
            ),
        },
    }


def _catalog_inputs(paths: Iterable[str], *, kind: str) -> List[Dict[str, str]]:
    return [
        {"path": path, "kind": _catalog_kind(path)}
        for path in paths
        if _catalog_matches_kind(path, kind=kind)
    ]


def _catalog_matches_kind(path: str, *, kind: str) -> bool:
    catalog_kind = _catalog_kind(path)
    if kind == "reference":
        return catalog_kind == "reference"
    return catalog_kind == "fallback"


def _catalog_kind(path: str) -> str:
    return "reference" if Path(path).name.startswith("catalog_00_") else "fallback"


def _source_readiness(inspection: Dict[str, Any]) -> List[Dict[str, Any]]:
    readiness: List[Dict[str, Any]] = []
    for item in inspection.get("reaction_evidence", []):
        readiness.append(
            {
                "kind": item.get("kind"),
                "source_system": item.get("source_system"),
                "source_name": item.get("source_name"),
                "status": item.get("status"),
                "next_step": item.get("next_step"),
                "record_count": item.get("record_count"),
                "query_count": item.get("query_count"),
                "path": item.get("path"),
                "url": item.get("url"),
            }
        )
    return readiness


def _configured_sources(
    runtime: AppRuntime,
    *,
    enabled: bool,
    allowed_source_systems: Iterable[str],
) -> List[Dict[str, Any]]:
    if not enabled:
        return []
    allowed = {item.lower() for item in allowed_source_systems}
    configured: List[Dict[str, Any]] = []
    for spec in runtime.config.bootstrap.reaction_evidence.sources:
        resolved_source_system = spec.source_system or spec.kind.split("_", 1)[0]
        source_system = resolved_source_system.lower()
        if allowed and source_system not in allowed:
            continue
        configured.append(
            {
                "kind": spec.kind,
                "source_system": resolved_source_system,
                "source_name": spec.source_name,
                "path": spec.path,
                "url": spec.url,
            }
        )
    return configured


def _catalog_template_metadata_counts(
    catalog: TemplateCatalog,
    *,
    origins: set[str],
    key: str,
) -> List[Dict[str, Any]]:
    counts: dict[str, int] = {}
    for template in catalog.templates:
        origin = str(template.metadata.get("template_origin") or "")
        if origin not in origins:
            continue
        value = template.metadata.get(key)
        if not value:
            continue
        text = str(value)
        counts[text] = counts.get(text, 0) + 1
    return [
        {"name": name, "count": counts[name]}
        for name in sorted(counts)
    ]


def _count_named_items(items: Iterable[Dict[str, Any]], *, allowed_names: set[str]) -> int:
    total = 0
    for item in items:
        if item.get("name") in allowed_names:
            total += int(item.get("count", 0))
    return total
