from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
import json

from .adapters import (
    AtctSnapshotAdapter,
    NistAsdBootstrapAdapter,
    PubChemIdentityAdapter,
    ReactionEvidenceFactory,
    VamdcTapClient,
)
from .adapters.http import SimpleHttpClient
from .catalog import TemplateCatalog
from .config import BuildConfig, EvidenceSourceSpec
from .normalization import AliasResolver
from .source_profiles import SourceStrengthRegistry
from .version import __version__


LIVE_KINDS = {"vamdc_live"}
LOCAL_EVIDENCE_KINDS = {
    "nist_kinetics_snapshot",
    "qdb_snapshot",
    "umist_ratefile",
    "kida_network",
    "vamdc_xsams",
}



def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()



def _iso_mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).replace(microsecond=0).isoformat()



def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()



def _status_for_path(path: Optional[str], *, with_hash: bool = True) -> Dict[str, Any]:
    if not path:
        return {"path": None, "exists": False}
    target = Path(path)
    if not target.exists():
        return {"path": str(target), "exists": False}
    payload: Dict[str, Any] = {
        "path": str(target),
        "exists": True,
        "size_bytes": target.stat().st_size,
        "modified_at": _iso_mtime(target),
    }
    if with_hash:
        payload["sha256"] = _sha256_file(target)
    return payload



def _feed_queries(config: BuildConfig) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for feed in config.feeds:
        query = feed.identity_query or feed.display_name or feed.formula
        out.append(
            {
                "species_key": feed.species_key,
                "formula": feed.formula,
                "query": query,
                "namespace": feed.identity_namespace,
            }
        )
    return out



def _config_hash(config: BuildConfig) -> str:
    payload = json.dumps(config.as_dict(), sort_keys=True, ensure_ascii=False).encode("utf-8")
    return sha256(payload).hexdigest()



def _report_next_step(*, status: str, mode: str) -> str:
    if status == "missing_path":
        return "snapshot_or_export_required"
    if status == "query_ready" and mode == "live":
        return "optional_head_preflight"
    if status == "ready":
        return "ready_for_build"
    if status == "disabled":
        return "disabled"
    if status == "no_query":
        return "query_configuration_required"
    if status == "error":
        return "inspect_error"
    return status



def inspect_sources(
    config: BuildConfig,
    *,
    head_vamdc: bool = False,
    http: Optional[SimpleHttpClient] = None,
    alias_resolver: Optional[AliasResolver] = None,
    strength_registry: Optional[SourceStrengthRegistry] = None,
) -> Dict[str, Any]:
    http_client = http or SimpleHttpClient()
    alias_resolver = alias_resolver or AliasResolver.empty()
    strength_registry = strength_registry or SourceStrengthRegistry.from_path(config.source_profiles_path)
    report = _base_inspection_report(config, alias_resolver=alias_resolver)
    report["pubchem"] = _inspect_pubchem(config)
    report["nist_asd"] = _inspect_nist_asd(config)
    report["atct"] = _inspect_atct(config)

    factory = ReactionEvidenceFactory(http=http_client, alias_resolver=alias_resolver, strength_registry=strength_registry)
    evidence_items, ready_count = _inspect_reaction_evidence_sources(
        config,
        factory=factory,
        head_vamdc=head_vamdc,
        http=http_client,
        strength_registry=strength_registry,
    )
    report["reaction_evidence"] = evidence_items
    report["summary"] = _inspection_summary(
        config,
        report["pubchem"],
        report["nist_asd"],
        report["atct"],
        ready_count=ready_count,
        total_sources=len(config.bootstrap.reaction_evidence.sources),
    )
    return report


def _base_inspection_report(
    config: BuildConfig,
    *,
    alias_resolver: AliasResolver,
) -> Dict[str, Any]:
    return {
        "generated_at": _utc_now(),
        "package_version": __version__,
        "config_path": config.config_path,
        "config_sources": list(config.config_sources),
        "config_sha256": _config_hash(config),
        "feeds": [feed.as_dict() for feed in config.feeds],
        "catalog_policy": config.catalog_policy.as_dict(),
        "state_masters": [spec.as_dict() for spec in config.state_masters],
        "state_filters": config.state_filters.as_dict(),
        "state_promotions": config.state_promotions.as_dict(),
        "template_promotions": config.template_promotions.as_dict(),
        "alias_path": config.alias_path,
        "alias_count": len(alias_resolver.alias_map),
        "excited_state_registry_path": config.excited_state_registry_path,
        "excited_state_registry_entries": alias_resolver.excited_state_registry.entry_count(),
        "source_profiles_path": config.source_profiles_path,
        "pubchem": {},
        "nist_asd": {},
        "atct": {},
        "reaction_evidence": [],
    }


def _inspect_pubchem(config: BuildConfig) -> Dict[str, Any]:
    pubchem = config.bootstrap.pubchem
    report = {
        "enabled": pubchem.enabled,
        "live_api": pubchem.live_api,
        "snapshot": _status_for_path(pubchem.snapshot_path),
        "queries": _feed_queries(config),
        "next_step": "disabled",
    }
    if pubchem.enabled:
        report["next_step"] = "ready_for_lookup" if pubchem.live_api else "freeze_snapshot_recommended"
    if pubchem.enabled and pubchem.snapshot_path and Path(pubchem.snapshot_path).exists():
        try:
            payload = json.loads(Path(pubchem.snapshot_path).read_text(encoding="utf-8"))
            report["snapshot_entries"] = len(payload)
            report["next_step"] = "ready_for_build"
        except Exception as exc:  # pragma: no cover - defensive
            report["error"] = str(exc)
            report["next_step"] = "inspect_error"
    return report


def _inspect_nist_asd(config: BuildConfig) -> Dict[str, Any]:
    asd = config.bootstrap.nist_asd
    asd_paths = [_status_for_path(path) for path in asd.export_paths]
    report = {
        "enabled": asd.enabled,
        "max_ion_charge": asd.max_ion_charge,
        "max_levels_per_spectrum": asd.max_levels_per_spectrum,
        "exports": asd_paths,
        "next_step": "disabled",
    }
    if asd.enabled:
        report["next_step"] = "asd_exports_required"
    if asd.enabled and asd.export_paths and all(item["exists"] for item in asd_paths):
        try:
            adapter = NistAsdBootstrapAdapter(asd.export_paths)
            spectra = sorted(adapter.levels_by_spectrum)
            total_levels = sum(len(items) for items in adapter.levels_by_spectrum.values())
            boot = adapter.bootstrap(
                [feed.formula for feed in config.feeds],
                max_ion_charge=asd.max_ion_charge,
                max_levels_per_spectrum=asd.max_levels_per_spectrum,
            )
            report["spectrum_count"] = len(spectra)
            report["total_levels"] = total_levels
            report["bootstrap_species_count"] = len(boot)
            report["spectra"] = spectra
            report["next_step"] = "ready_for_build"
        except Exception as exc:  # pragma: no cover - defensive
            report["error"] = str(exc)
            report["next_step"] = "inspect_error"
    return report


def _inspect_atct(config: BuildConfig) -> Dict[str, Any]:
    atct = config.bootstrap.atct
    report = {
        "enabled": atct.enabled,
        "snapshot": _status_for_path(atct.snapshot_path),
        "soft_endothermic_kj_mol": atct.soft_endothermic_kj_mol,
        "hard_endothermic_kj_mol": atct.hard_endothermic_kj_mol,
        "prunable_families": list(atct.prunable_families),
        "next_step": "disabled",
    }
    if atct.enabled:
        report["next_step"] = "atct_snapshot_required"
    if atct.enabled and atct.snapshot_path and Path(atct.snapshot_path).exists():
        try:
            adapter = AtctSnapshotAdapter(atct.snapshot_path)
            report["entry_count"] = len(adapter.entries)
            report["next_step"] = "ready_for_build"
        except Exception as exc:  # pragma: no cover - defensive
            report["error"] = str(exc)
            report["next_step"] = "inspect_error"
    return report


def _inspect_reaction_evidence_sources(
    config: BuildConfig,
    *,
    factory: ReactionEvidenceFactory,
    head_vamdc: bool,
    http: SimpleHttpClient,
    strength_registry: SourceStrengthRegistry,
) -> Tuple[List[Dict[str, Any]], int]:
    feed_formulas = [feed.formula for feed in config.feeds]
    items: List[Dict[str, Any]] = []
    ready_count = 0
    for spec in config.bootstrap.reaction_evidence.sources:
        item = inspect_evidence_source(
            spec,
            feed_formulas=feed_formulas,
            factory=factory,
            head_vamdc=head_vamdc,
            http=http,
            strength_registry=strength_registry,
        )
        if item.get("status") in {"ready", "query_ready"}:
            ready_count += 1
        items.append(item)
    return items, ready_count


def _inspection_summary(
    config: BuildConfig,
    pubchem_report: Dict[str, Any],
    asd_report: Dict[str, Any],
    atct_report: Dict[str, Any],
    *,
    ready_count: int,
    total_sources: int,
) -> Dict[str, Any]:
    evidence_required = _requires_reaction_evidence(config, total_sources=total_sources)
    evidence_ready = ready_count >= 1 if evidence_required else True
    bootstrap_ready = (
        _bootstrap_component_ready(pubchem_report)
        and _bootstrap_component_ready(asd_report)
        and _bootstrap_component_ready(atct_report)
    )
    return {
        "reaction_evidence_required": evidence_required,
        "reaction_evidence_ready": ready_count,
        "reaction_evidence_total": total_sources,
        "bootstrap_ready": bootstrap_ready,
        "build_ready": bootstrap_ready and evidence_ready,
    }


def _bootstrap_component_ready(report: Dict[str, Any]) -> bool:
    return report.get("next_step") in {
        "disabled",
        "ready_for_build",
        "ready_for_lookup",
        "freeze_snapshot_recommended",
    }


def _requires_reaction_evidence(config: BuildConfig, *, total_sources: int) -> bool:
    if config.state_promotions.molecular_excited_states.enabled:
        return True
    if config.template_promotions.source_backed_templates.enabled:
        return True
    if config.template_promotions.molecular_excited_state_templates.enabled:
        return True
    if config.bootstrap.reaction_evidence.seed_templates and total_sources >= 1:
        return True
    return False



def inspect_evidence_source(
    spec: EvidenceSourceSpec,
    *,
    feed_formulas: Iterable[str],
    factory: ReactionEvidenceFactory,
    head_vamdc: bool,
    http: SimpleHttpClient,
    strength_registry: SourceStrengthRegistry,
) -> Dict[str, Any]:
    kind = spec.kind.lower()
    source_system = spec.source_system or kind.split("_", 1)[0]
    profile = strength_registry.profile_for(source_system)
    item: Dict[str, Any] = {
        "kind": spec.kind,
        "enabled": spec.enabled,
        "source_name": spec.source_name,
        "source_system": source_system,
        "path": spec.path,
        "url": spec.url,
        "note": spec.note,
        "mode": "live" if kind in LIVE_KINDS else "snapshot",
        "profile_family": profile.family if profile else None,
        "profile_priority": profile.priority if profile else None,
        "profile_default_support": profile.default_support if profile else None,
    }
    if not spec.enabled:
        item["status"] = "disabled"
        item["next_step"] = "disabled"
        return item

    if spec.path:
        item["path_status"] = _status_for_path(spec.path)
        if not item["path_status"]["exists"]:
            item["status"] = "missing_path"
            item["next_step"] = _report_next_step(status="missing_path", mode=item["mode"])
            return item

    try:
        if kind in LOCAL_EVIDENCE_KINDS:
            index = factory.build_indexes([spec], feed_formulas=feed_formulas)[0]
            item["status"] = "ready"
            item["record_count"] = len(index.entries)
            item["example_reaction"] = _example_signature(index.entries)
            item["next_step"] = _report_next_step(status="ready", mode=item["mode"])
            return item

        if kind == "vamdc_live":
            queries = factory.expand_vamdc_queries(spec, feed_formulas=list(feed_formulas))
            item["query_count"] = len(queries)
            item["queries"] = queries[:5]
            item["status"] = "query_ready" if queries else "no_query"
            item["next_step"] = _report_next_step(status=item["status"], mode=item["mode"])
            if head_vamdc and spec.url and queries:
                client = VamdcTapClient(http=http)
                counts = []
                for query in queries[:3]:
                    try:
                        headers = client.head_counts(url=spec.url, query=query)
                        counts.append(
                            {
                                "query": query,
                                "headers": headers,
                                "last_modified": headers.get("Last-Modified") or headers.get("last-modified"),
                                "etag": headers.get("ETag") or headers.get("etag"),
                            }
                        )
                    except Exception as exc:  # pragma: no cover - network-dependent
                        counts.append({"query": query, "error": str(exc)})
                item["head_counts"] = counts
            return item

        item["status"] = "unsupported_kind"
        item["next_step"] = item["status"]
        return item
    except Exception as exc:  # pragma: no cover - defensive
        item["status"] = "error"
        item["error"] = str(exc)
        item["next_step"] = _report_next_step(status="error", mode=item["mode"])
        return item



def _example_signature(entries: Iterable[Any]) -> Optional[str]:
    for entry in entries:
        try:
            lhs = " + ".join(entry.reactants)
            rhs = " + ".join(entry.products)
            return f"{lhs} -> {rhs}"
        except Exception:  # pragma: no cover - defensive
            continue
    return None



def build_evidence_manifest(indexes: Iterable[Any], *, config_path: Optional[str]) -> Dict[str, Any]:
    per_source: List[Dict[str, Any]] = []
    total = 0
    for index in indexes:
        count = len(index.entries)
        total += count
        source_name = index.entries[0].source_name if index.entries else index.source_id
        acquisition_method = index.entries[0].acquisition_method if index.entries else None
        evidence_kind = index.entries[0].evidence_kind if index.entries else None
        first_meta = dict(index.entries[0].metadata) if index.entries else {}
        per_source.append(
            {
                "source_id": index.source_id,
                "source_name": source_name,
                "record_count": count,
                "acquisition_method": acquisition_method,
                "evidence_kind": evidence_kind,
                "source_family": first_meta.get("source_family"),
                "source_priority": first_meta.get("source_priority"),
            }
        )
    per_source.sort(key=lambda item: (item["source_id"], item["source_name"]))
    return {
        "generated_at": _utc_now(),
        "config_path": config_path,
        "total_records": total,
        "sources": per_source,
    }


def build_catalog_manifest(
    catalog: TemplateCatalog,
    *,
    config_path: Optional[str],
    reaction_conflict_policy: str,
) -> Dict[str, Any]:
    species_by_origin = _count_named_items(
        (
            str(proto.metadata.get("state_origin") or "unknown")
            for proto in catalog.species_library.values()
        )
    )
    templates_by_origin = _count_named_items(
        (
            str(template.metadata.get("template_origin") or "unknown")
            for template in catalog.templates
        )
    )
    templates_by_layer = _count_named_items(
        (
            str(template.metadata.get("template_layer") or "unknown")
            for template in catalog.templates
        )
    )
    template_source_systems = _count_named_items(
        _iter_template_source_systems(catalog.templates)
    )
    template_source_names = _count_named_items(
        _iter_template_metadata_values(catalog.templates, key="template_source_name")
    )
    merge_actions = _count_named_items(
        event.get("action", "unknown")
        for event in catalog.template_merge_events
    )
    conflicts = [
        dict(event)
        for event in catalog.template_merge_events
        if event.get("action") != "added"
    ]
    return {
        "generated_at": _utc_now(),
        "config_path": config_path,
        "loaded_resources": list(catalog.loaded_resources),
        "reaction_conflict_policy": reaction_conflict_policy,
        "species_count": len(catalog.species_library),
        "template_count": len(catalog.templates),
        "species_by_origin": species_by_origin,
        "templates_by_origin": templates_by_origin,
        "templates_by_layer": templates_by_layer,
        "template_source_systems": template_source_systems,
        "template_source_names": template_source_names,
        "merge_action_summary": merge_actions,
        "equation_conflicts": conflicts,
    }



def build_pubchem_snapshot(
    config: BuildConfig,
    *,
    live_api: bool,
    existing_path: Optional[str] = None,
    only_missing: bool = False,
) -> Dict[str, Dict[str, Any]]:
    adapter = PubChemIdentityAdapter(
        snapshot_path=config.bootstrap.pubchem.snapshot_path,
        live_api=live_api,
    )
    payload: Dict[str, Dict[str, Any]] = {}
    if existing_path and Path(existing_path).exists():
        payload.update(json.loads(Path(existing_path).read_text(encoding="utf-8")))
    for feed in config.feeds:
        query = feed.identity_query or feed.display_name or feed.formula
        namespace = feed.identity_namespace
        key = adapter.snapshot_key(namespace, query)
        if only_missing and key in payload:
            continue
        record = adapter.resolve(query=query, namespace=namespace)
        if record is None:
            continue
        payload[key] = adapter.record_to_snapshot_payload(record)
    return payload



def _evidence_record_key(record: Dict[str, Any]) -> Tuple[Any, ...]:
    return (
        record.get("source_system"),
        record.get("source_name"),
        tuple(record.get("reactants", [])),
        tuple(record.get("products", [])),
        record.get("citation"),
        record.get("source_url"),
    )



def merge_evidence_payloads(existing: Optional[Dict[str, Any]], new: Dict[str, Any]) -> Dict[str, Any]:
    if not existing:
        return new
    merged_records: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
    carried = 0
    for record in existing.get("records", []):
        merged_records[_evidence_record_key(record)] = dict(record)
        carried += 1
    replaced = 0
    added = 0
    for record in new.get("records", []):
        key = _evidence_record_key(record)
        if key in merged_records:
            replaced += 1
        else:
            added += 1
        merged_records[key] = dict(record)
    payload = {
        "manifest": dict(new.get("manifest", {})),
        "records": list(merged_records.values()),
        "merge_summary": {
            "carried_over_records": carried,
            "new_unique_records": added,
            "replaced_records": replaced,
            "final_record_count": len(merged_records),
        },
    }
    payload["manifest"]["total_records"] = len(merged_records)
    return payload



def load_json_if_exists(path: Optional[str]) -> Optional[Dict[str, Any]]:
    if not path:
        return None
    target = Path(path)
    if not target.exists():
        return None
    return json.loads(target.read_text(encoding="utf-8"))



def build_source_lock(
    config: BuildConfig,
    *,
    inspection_report: Dict[str, Any],
    evidence_manifest: Optional[Dict[str, Any]] = None,
    catalog_manifest: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "generated_at": _utc_now(),
        "package_version": __version__,
        "config_path": config.config_path,
        "config_sha256": _config_hash(config),
        "config_sources": list(config.config_sources),
        "feeds": [feed.as_dict() for feed in config.feeds],
        "projectiles": list(config.projectiles),
        "libraries": list(config.libraries),
        "catalog_paths": list(config.catalog_paths),
        "catalog_policy": config.catalog_policy.as_dict(),
        "state_masters": [spec.as_dict() for spec in config.state_masters],
        "state_filters": config.state_filters.as_dict(),
        "state_promotions": config.state_promotions.as_dict(),
        "template_promotions": config.template_promotions.as_dict(),
        "alias_path": config.alias_path,
        "excited_state_registry_path": config.excited_state_registry_path,
        "source_profiles_path": config.source_profiles_path,
        "inspection": inspection_report,
        "evidence_manifest": evidence_manifest,
        "catalog_manifest": catalog_manifest,
    }


def _count_named_items(values: Iterable[str]) -> List[Dict[str, Any]]:
    counts: Dict[str, int] = {}
    for value in values:
        if not value:
            continue
        counts[value] = counts.get(value, 0) + 1
    return [
        {"name": name, "count": counts[name]}
        for name in sorted(counts)
    ]


def _iter_template_source_systems(templates: Iterable[Any]) -> Iterable[str]:
    for template in templates:
        source_system = template.metadata.get("template_source_system")
        if isinstance(source_system, str) and source_system:
            yield source_system
        for name in template.metadata.get("reference_source_systems", []) or []:
            if isinstance(name, str) and name:
                yield name


def _iter_template_metadata_values(templates: Iterable[Any], *, key: str) -> Iterable[str]:
    for template in templates:
        value = template.metadata.get(key)
        if isinstance(value, str) and value:
            yield value
