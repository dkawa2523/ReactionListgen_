from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from importlib.resources import files as resource_files
from pathlib import Path
from typing import Any, Dict, Iterable, List

import yaml

from .formula import parse_species_token
from .model import MissingProductSpec, ReactionTemplate, SpeciesPrototype
from .provenance import EvidenceRecord


DEFAULT_CATALOG_TEMPLATE_PRIORITY = 20
DEFAULT_EXTERNAL_SEED_TEMPLATE_PRIORITY = 40
DEFAULT_PROMOTED_TEMPLATE_PRIORITY = 60
DEFAULT_EXCITED_TEMPLATE_PRIORITY = 70


@lru_cache(maxsize=8)
def _load_yaml_resource(filename: str) -> Dict[str, Any]:
    resource = resource_files("plasma_reaction_builder.data").joinpath(filename)
    return yaml.safe_load(resource.read_text(encoding="utf-8")) or {}


@lru_cache(maxsize=1)
def load_packaged_species_library() -> Dict[str, SpeciesPrototype]:
    payload = _load_yaml_resource("species_library.yaml")
    return _payload_to_species(
        payload,
        resource_label="packaged:species_library.yaml",
        state_origin="packaged_species_library",
    )


@lru_cache(maxsize=1)
def load_reference_library() -> Dict[str, Dict[str, Any]]:
    payload = _load_yaml_resource("references.yaml")
    return payload.get("references", {})



def _reference_to_evidence(ref_id: str, references: Dict[str, Dict[str, Any]]) -> EvidenceRecord:
    entry = references.get(ref_id)
    if not entry:
        return EvidenceRecord(
            source_system="template_library",
            source_name="packaged_reference_placeholder",
            acquisition_method="package_template",
            evidence_kind="parser_event",
            support_score=0.20,
            locator=ref_id,
            note="Unknown reference id in template library.",
        )
    return EvidenceRecord(
        source_system=entry["source_system"],
        source_name=entry["source_name"],
        acquisition_method=entry["acquisition_method"],
        evidence_kind=entry["evidence_kind"],
        support_score=float(entry["support_score"]),
        source_url=entry.get("source_url"),
        locator=entry.get("locator", ref_id),
        citation=entry.get("citation"),
        note=entry.get("note"),
    )



def _iter_yaml_files(paths: Iterable[str | Path]) -> Iterable[Path]:
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            for child in sorted(path.glob("*.y*ml")):
                yield child
        elif path.is_file():
            yield path
        else:
            raise FileNotFoundError(f"Catalog path not found: {path}")



def _payload_to_species(
    payload: Dict[str, Any],
    *,
    resource_label: str,
    state_origin: str,
) -> Dict[str, SpeciesPrototype]:
    species: Dict[str, SpeciesPrototype] = {}
    for entry in payload.get("species", []):
        metadata = dict(entry.get("metadata", {}))
        metadata.setdefault("state_origin", state_origin)
        metadata.setdefault("catalog_resource", resource_label)
        species[entry["key"]] = SpeciesPrototype(
            **{key: value for key, value in entry.items() if key != "metadata"},
            metadata=metadata,
        )
    return species


def _charge_allowed(charge: int, *, charge_window_min: int | None, charge_window_max: int | None) -> bool:
    if charge_window_min is not None and charge < charge_window_min:
        return False
    if charge_window_max is not None and charge > charge_window_max:
        return False
    return True


def _filter_species_by_charge(
    species: Iterable[SpeciesPrototype],
    *,
    charge_window_min: int | None,
    charge_window_max: int | None,
) -> Dict[str, SpeciesPrototype]:
    filtered: Dict[str, SpeciesPrototype] = {}
    for prototype in species:
        if not _charge_allowed(
            prototype.charge,
            charge_window_min=charge_window_min,
            charge_window_max=charge_window_max,
        ):
            continue
        filtered[prototype.key] = prototype
    return filtered


def _template_within_charge_window(
    template: ReactionTemplate,
    *,
    charge_window_min: int | None,
    charge_window_max: int | None,
) -> bool:
    for key in list(template.reactants) + list(template.products):
        charge = parse_species_token(key).charge
        if not _charge_allowed(
            charge,
            charge_window_min=charge_window_min,
            charge_window_max=charge_window_max,
        ):
            return False
    return True



def _payload_to_reactions(
    payload: Dict[str, Any],
    references: Dict[str, Dict[str, Any]],
    *,
    resource_label: str,
    template_origin: str,
    template_priority: int,
) -> List[ReactionTemplate]:
    templates: List[ReactionTemplate] = []
    for entry in payload.get("reactions", []):
        evidence = [_reference_to_evidence(ref_id, references) for ref_id in entry.get("reference_ids", [])]
        metadata = dict(entry.get("metadata", {}))
        metadata.setdefault("template_origin", template_origin)
        metadata.setdefault("template_layer", "catalog")
        metadata.setdefault("template_priority", template_priority)
        metadata.setdefault("catalog_resource", resource_label)
        metadata.setdefault(
            "reference_source_systems",
            sorted({record.source_system for record in evidence if record.source_system}),
        )
        metadata.setdefault(
            "reference_source_names",
            sorted({record.source_name for record in evidence if record.source_name}),
        )
        template = ReactionTemplate(
            key=entry["key"],
            reactants=list(entry["reactants"]),
            products=list(entry.get("products", [])),
            lhs_tokens=list(entry["lhs_tokens"]),
            rhs_tokens=list(entry.get("rhs_tokens", [])),
            family=entry["family"],
            required_projectile=entry.get("required_projectile"),
            threshold_ev=entry.get("threshold_ev"),
            delta_h_kj_mol=entry.get("delta_h_kj_mol"),
            base_confidence=float(entry.get("base_confidence", 0.60)),
            evidence=evidence,
            reference_ids=list(entry.get("reference_ids", [])),
            note=entry.get("note"),
            inferred_balance=bool(entry.get("inferred_balance", False)),
            missing_products=[MissingProductSpec(**spec) for spec in entry.get("missing_products", [])],
            metadata=metadata,
        )
        templates.append(template)
    return templates


@dataclass(slots=True)
class TemplateMergeStats:
    added: int = 0
    replaced: int = 0
    skipped: int = 0

    def as_dict(self) -> Dict[str, int]:
        return {
            "added": self.added,
            "replaced": self.replaced,
            "skipped": self.skipped,
        }


@dataclass(slots=True)
class TemplateCatalog:
    species_library: Dict[str, SpeciesPrototype]
    templates: List[ReactionTemplate]
    loaded_resources: List[str] = field(default_factory=list)
    template_merge_events: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_sources(
        cls,
        libraries: Iterable[str],
        catalog_paths: Iterable[str | Path],
        *,
        charge_window_min: int | None = None,
        charge_window_max: int | None = None,
    ) -> "TemplateCatalog":
        species = _filter_species_by_charge(
            load_packaged_species_library().values(),
            charge_window_min=charge_window_min,
            charge_window_max=charge_window_max,
        )
        references = dict(load_reference_library())
        resources = ["packaged:species_library.yaml", "packaged:references.yaml"]
        catalog = cls(species_library=species, templates=[], loaded_resources=resources)

        for lib in libraries:
            filename = f"reactions_{lib}.yaml"
            payload = _load_yaml_resource(filename)
            catalog.merge_templates(
                (
                    template
                    for template in _payload_to_reactions(
                        payload,
                        references,
                        resource_label=f"packaged:{filename}",
                        template_origin="packaged_library",
                        template_priority=DEFAULT_CATALOG_TEMPLATE_PRIORITY,
                    )
                    if _template_within_charge_window(
                        template,
                        charge_window_min=charge_window_min,
                        charge_window_max=charge_window_max,
                    )
                ),
                equation_conflict_policy="keep_existing",
                merge_reason=f"load:packaged:{filename}",
            )
            catalog.loaded_resources.append(f"packaged:{filename}")

        for path in _iter_yaml_files(catalog_paths):
            payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            resource_label = str(path)
            catalog.loaded_resources.append(resource_label)
            if payload.get("references"):
                for key, value in payload.get("references", {}).items():
                    references[key] = dict(value)
            species.update(
                _filter_species_by_charge(
                    _payload_to_species(
                        payload,
                        resource_label=resource_label,
                        state_origin="catalog_species",
                    ).values(),
                    charge_window_min=charge_window_min,
                    charge_window_max=charge_window_max,
                )
            )
            catalog.merge_templates(
                (
                    template
                    for template in _payload_to_reactions(
                        payload,
                        references,
                        resource_label=resource_label,
                        template_origin="curated_catalog",
                        template_priority=DEFAULT_CATALOG_TEMPLATE_PRIORITY,
                    )
                    if _template_within_charge_window(
                        template,
                        charge_window_min=charge_window_min,
                        charge_window_max=charge_window_max,
                    )
                ),
                equation_conflict_policy="keep_existing",
                merge_reason=f"load:{resource_label}",
            )

        return catalog

    def get_species(self, key: str) -> SpeciesPrototype | None:
        return self.species_library.get(key)

    def ensure_species(self, key: str, formula: str, charge: int = 0, state_class: str = "ground", **kwargs: Any) -> SpeciesPrototype:
        existing = self.species_library.get(key)
        if existing:
            return existing
        proto = SpeciesPrototype(key=key, display_name=key, formula=formula, charge=charge, state_class=state_class, **kwargs)
        self.species_library[key] = proto
        return proto

    def merge_species(self, prototypes: Iterable[SpeciesPrototype]) -> int:
        added = 0
        for proto in prototypes:
            if proto.key not in self.species_library:
                self.species_library[proto.key] = proto
                added += 1
        return added

    def merge_templates(
        self,
        templates: Iterable[ReactionTemplate],
        *,
        equation_conflict_policy: str = "keep_existing",
        merge_reason: str | None = None,
    ) -> TemplateMergeStats:
        existing_keys = {template.key: index for index, template in enumerate(self.templates)}
        existing_equations = {template.equation(): index for index, template in enumerate(self.templates)}
        stats = TemplateMergeStats()
        for template in templates:
            existing_key_index = existing_keys.get(template.key)
            if existing_key_index is not None:
                stats.skipped += 1
                self.template_merge_events.append(
                    _template_merge_event(
                        action="skipped_duplicate_key",
                        incoming=template,
                        existing=self.templates[existing_key_index],
                        reason=merge_reason,
                    )
                )
                continue
            equation = template.equation()
            existing_equation_index = existing_equations.get(equation)
            if existing_equation_index is not None:
                existing = self.templates[existing_equation_index]
                if _should_replace_template(
                    existing,
                    incoming=template,
                    equation_conflict_policy=equation_conflict_policy,
                ):
                    del existing_keys[existing.key]
                    self.templates[existing_equation_index] = template
                    existing_keys[template.key] = existing_equation_index
                    existing_equations[equation] = existing_equation_index
                    stats.replaced += 1
                    self.template_merge_events.append(
                        _template_merge_event(
                            action="replaced_equation_match",
                            incoming=template,
                            existing=existing,
                            reason=merge_reason,
                        )
                    )
                else:
                    stats.skipped += 1
                    self.template_merge_events.append(
                        _template_merge_event(
                            action="skipped_equation_match",
                            incoming=template,
                            existing=existing,
                            reason=merge_reason,
                        )
                    )
                continue
            self.templates.append(template)
            existing_keys[template.key] = len(self.templates) - 1
            existing_equations[equation] = len(self.templates) - 1
            stats.added += 1
            self.template_merge_events.append(
                _template_merge_event(
                    action="added",
                    incoming=template,
                    existing=None,
                    reason=merge_reason,
                )
            )
        return stats


def _template_priority(template: ReactionTemplate) -> int:
    value = template.metadata.get("template_priority")
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _should_replace_template(
    existing: ReactionTemplate,
    *,
    incoming: ReactionTemplate,
    equation_conflict_policy: str,
) -> bool:
    if equation_conflict_policy == "prefer_incoming":
        return True
    if equation_conflict_policy == "prefer_higher_priority":
        return _template_priority(incoming) > _template_priority(existing)
    return False


def _template_merge_event(
    *,
    action: str,
    incoming: ReactionTemplate,
    existing: ReactionTemplate | None,
    reason: str | None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "action": action,
        "reason": reason,
        "incoming_key": incoming.key,
        "incoming_equation": incoming.equation(),
        "incoming_origin": incoming.metadata.get("template_origin"),
        "incoming_priority": _template_priority(incoming),
    }
    if existing is not None:
        payload.update(
            {
                "existing_key": existing.key,
                "existing_origin": existing.metadata.get("template_origin"),
                "existing_priority": _template_priority(existing),
            }
        )
    return payload
