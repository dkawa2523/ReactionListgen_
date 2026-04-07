from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import json

import yaml


@dataclass(slots=True)
class FeedSpec:
    species_key: str
    formula: str
    display_name: Optional[str] = None
    identity_query: Optional[str] = None
    identity_namespace: str = "name"

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Limits:
    max_generation: int = 3
    beam_width: int = 64
    max_species: int = 2000

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Conditions:
    electron_max_ev: float = 100.0
    ion_max_ev: float = 200.0
    gas_temperature_k: float = 300.0

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class StateFilterOptions:
    charge_window_min: Optional[int] = None
    charge_window_max: Optional[int] = None

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def allows_charge(self, charge: int) -> bool:
        if self.charge_window_min is not None and charge < self.charge_window_min:
            return False
        if self.charge_window_max is not None and charge > self.charge_window_max:
            return False
        return True


@dataclass(slots=True)
class StateMasterSourceSpec:
    path: str
    families: List[str] = field(default_factory=list)
    include_disabled: bool = False

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MolecularExcitedStatePromotionOptions:
    enabled: bool = False
    source_systems: List[str] = field(default_factory=lambda: ["qdb", "ideadb", "vamdc"])
    min_support_score: float = 0.75
    max_states_per_species: int = 4
    require_electron_signal: bool = True

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class StatePromotionOptions:
    molecular_excited_states: MolecularExcitedStatePromotionOptions = field(default_factory=MolecularExcitedStatePromotionOptions)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "molecular_excited_states": self.molecular_excited_states.as_dict(),
        }


@dataclass(slots=True)
class SourceBackedTemplatePromotionOptions:
    enabled: bool = False
    source_systems: List[str] = field(default_factory=lambda: ["qdb", "nist_kinetics", "umist", "kida", "vamdc", "ideadb"])
    target_families: List[str] = field(default_factory=list)
    allowed_reaction_families: List[str] = field(
        default_factory=lambda: [
            "electron_attachment",
            "electron_excitation",
            "electron_excitation_vibrational",
            "electron_ionization",
            "electron_dissociation",
            "charge_transfer",
            "radical_neutral_reaction",
            "ion_neutral_followup",
            "dissociative_recombination",
            "mutual_neutralization",
        ]
    )
    min_support_score: float = 0.75
    max_templates_per_family: int = 8
    require_catalog_species: bool = True

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MolecularExcitedStateTemplatePromotionOptions:
    enabled: bool = False
    source_systems: List[str] = field(default_factory=lambda: ["qdb", "ideadb", "vamdc"])
    target_families: List[str] = field(default_factory=list)
    min_support_score: float = 0.75
    include_electron_excitation: bool = True
    include_radiative_relaxation: bool = True
    include_collisional_quenching: bool = True
    include_superelastic_deexcitation: bool = False
    quenching_partners: Dict[str, List[str]] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TemplatePromotionOptions:
    source_backed_templates: SourceBackedTemplatePromotionOptions = field(default_factory=SourceBackedTemplatePromotionOptions)
    molecular_excited_state_templates: MolecularExcitedStateTemplatePromotionOptions = field(default_factory=MolecularExcitedStateTemplatePromotionOptions)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "source_backed_templates": self.source_backed_templates.as_dict(),
            "molecular_excited_state_templates": self.molecular_excited_state_templates.as_dict(),
        }


@dataclass(slots=True)
class PubChemOptions:
    enabled: bool = True
    live_api: bool = False
    snapshot_path: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class NistAsdOptions:
    enabled: bool = True
    export_paths: List[str] = field(default_factory=list)
    max_ion_charge: int = 1
    max_levels_per_spectrum: int = 3

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AtctOptions:
    enabled: bool = True
    snapshot_path: Optional[str] = None
    soft_endothermic_kj_mol: float = 150.0
    hard_endothermic_kj_mol: float = 320.0
    prunable_families: List[str] = field(
        default_factory=lambda: [
            "neutral_fragmentation",
            "radical_fragmentation",
            "ion_fragmentation",
            "ion_neutral_followup",
            "gas_phase_evidence",
            "ion_neutral_evidence",
        ]
    )

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class EvidenceSourceSpec:
    kind: str
    path: Optional[str] = None
    url: Optional[str] = None
    source_name: Optional[str] = None
    source_system: Optional[str] = None
    query: Optional[str] = None
    queries: List[str] = field(default_factory=list)
    species_queries: List[str] = field(default_factory=list)
    query_template: Optional[str] = None
    support_score: Optional[float] = None
    include_special_processes: bool = False
    use_feed_formulas: bool = False
    enabled: bool = True
    note: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ReactionEvidenceOptions:
    sources: List[EvidenceSourceSpec] = field(default_factory=list)
    seed_templates: bool = True
    max_templates_per_source: int = 60
    require_reactant_overlap: bool = True

    def as_dict(self) -> Dict[str, Any]:
        return {
            "sources": [source.as_dict() for source in self.sources],
            "seed_templates": self.seed_templates,
            "max_templates_per_source": self.max_templates_per_source,
            "require_reactant_overlap": self.require_reactant_overlap,
        }


@dataclass(slots=True)
class BootstrapOptions:
    pubchem: PubChemOptions = field(default_factory=PubChemOptions)
    nist_asd: NistAsdOptions = field(default_factory=NistAsdOptions)
    atct: AtctOptions = field(default_factory=AtctOptions)
    reaction_evidence: ReactionEvidenceOptions = field(default_factory=ReactionEvidenceOptions)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "pubchem": self.pubchem.as_dict(),
            "nist_asd": self.nist_asd.as_dict(),
            "atct": self.atct.as_dict(),
            "reaction_evidence": self.reaction_evidence.as_dict(),
        }


@dataclass(slots=True)
class CatalogPolicyOptions:
    reaction_conflict_policy: str = "keep_existing"

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class BuildConfig:
    feeds: List[FeedSpec]
    projectiles: List[str] = field(default_factory=lambda: ["e-"])
    libraries: List[str] = field(default_factory=lambda: ["ch4", "c_c4f8"])
    catalog_paths: List[str] = field(default_factory=list)
    catalog_policy: CatalogPolicyOptions = field(default_factory=CatalogPolicyOptions)
    state_masters: List[StateMasterSourceSpec] = field(default_factory=list)
    state_filters: StateFilterOptions = field(default_factory=StateFilterOptions)
    state_promotions: StatePromotionOptions = field(default_factory=StatePromotionOptions)
    template_promotions: TemplatePromotionOptions = field(default_factory=TemplatePromotionOptions)
    limits: Limits = field(default_factory=Limits)
    conditions: Conditions = field(default_factory=Conditions)
    bootstrap: BootstrapOptions = field(default_factory=BootstrapOptions)
    alias_path: Optional[str] = None
    excited_state_registry_path: Optional[str] = None
    source_profiles_path: Optional[str] = None
    config_path: Optional[str] = None
    config_sources: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "feeds": [feed.as_dict() for feed in self.feeds],
            "projectiles": list(self.projectiles),
            "libraries": list(self.libraries),
            "catalog_paths": list(self.catalog_paths),
            "catalog_policy": self.catalog_policy.as_dict(),
            "state_masters": [spec.as_dict() for spec in self.state_masters],
            "state_filters": self.state_filters.as_dict(),
            "state_promotions": self.state_promotions.as_dict(),
            "template_promotions": self.template_promotions.as_dict(),
            "limits": self.limits.as_dict(),
            "conditions": self.conditions.as_dict(),
            "bootstrap": self.bootstrap.as_dict(),
            "alias_path": self.alias_path,
            "excited_state_registry_path": self.excited_state_registry_path,
            "source_profiles_path": self.source_profiles_path,
            "config_path": self.config_path,
            "config_sources": list(self.config_sources),
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), indent=2, ensure_ascii=False)



def _resolve_path(path_value: Optional[str], *, base_dir: Path) -> Optional[str]:
    if not path_value:
        return path_value
    candidate = Path(path_value)
    if candidate.is_absolute():
        return str(candidate)
    return str((base_dir / candidate).resolve())



def _resolve_paths(values: List[str], *, base_dir: Path) -> List[str]:
    return [_resolve_path(value, base_dir=base_dir) for value in values if value]



def _resolve_source_specs(raw_sources: List[Dict[str, Any]], *, base_dir: Path) -> List[EvidenceSourceSpec]:
    sources: List[EvidenceSourceSpec] = []
    for raw in raw_sources:
        payload = dict(raw)
        payload["path"] = _resolve_path(payload.get("path"), base_dir=base_dir)
        sources.append(EvidenceSourceSpec(**payload))
    return sources


def _resolve_state_master_specs(raw_specs: List[Dict[str, Any]], *, base_dir: Path) -> List[StateMasterSourceSpec]:
    specs: List[StateMasterSourceSpec] = []
    for raw in raw_specs:
        payload = dict(raw)
        payload["path"] = _resolve_path(payload.get("path"), base_dir=base_dir)
        specs.append(StateMasterSourceSpec(**payload))
    return specs



def _deep_merge_payload(base: Any, override: Any) -> Any:
    if isinstance(base, dict) and isinstance(override, dict):
        merged = dict(base)
        for key, value in override.items():
            if key in merged:
                merged[key] = _deep_merge_payload(merged[key], value)
            else:
                merged[key] = value
        return merged
    return override


def _dedupe_preserve_order(values: List[str]) -> List[str]:
    ordered: List[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        ordered.append(value)
        seen.add(value)
    return ordered


def _normalize_payload_paths(payload: Dict[str, Any], *, base_dir: Path) -> Dict[str, Any]:
    normalized = dict(payload)
    if "catalog_paths" in payload:
        normalized["catalog_paths"] = _resolve_paths(list(payload.get("catalog_paths", [])), base_dir=base_dir)
    if "alias_path" in payload:
        normalized["alias_path"] = _resolve_path(payload.get("alias_path"), base_dir=base_dir)
    if "excited_state_registry_path" in payload:
        normalized["excited_state_registry_path"] = _resolve_path(
            payload.get("excited_state_registry_path"),
            base_dir=base_dir,
        )
    if "source_profiles_path" in payload:
        normalized["source_profiles_path"] = _resolve_path(payload.get("source_profiles_path"), base_dir=base_dir)

    if "state_masters" in payload:
        state_masters = []
        for raw in payload.get("state_masters", []):
            item = dict(raw)
            item["path"] = _resolve_path(item.get("path"), base_dir=base_dir)
            state_masters.append(item)
        normalized["state_masters"] = state_masters

    if "bootstrap" in payload:
        bootstrap_payload = dict(payload.get("bootstrap", {}))

        if "pubchem" in bootstrap_payload:
            pubchem_payload = dict(bootstrap_payload.get("pubchem", {}))
            pubchem_payload["snapshot_path"] = _resolve_path(pubchem_payload.get("snapshot_path"), base_dir=base_dir)
            bootstrap_payload["pubchem"] = pubchem_payload

        if "nist_asd" in bootstrap_payload:
            nist_asd_payload = dict(bootstrap_payload.get("nist_asd", {}))
            nist_asd_payload["export_paths"] = _resolve_paths(list(nist_asd_payload.get("export_paths", [])), base_dir=base_dir)
            bootstrap_payload["nist_asd"] = nist_asd_payload

        if "atct" in bootstrap_payload:
            atct_payload = dict(bootstrap_payload.get("atct", {}))
            atct_payload["snapshot_path"] = _resolve_path(atct_payload.get("snapshot_path"), base_dir=base_dir)
            bootstrap_payload["atct"] = atct_payload

        if "reaction_evidence" in bootstrap_payload:
            reaction_evidence_payload = dict(bootstrap_payload.get("reaction_evidence", {}))
            if "sources" in reaction_evidence_payload:
                resolved_sources = []
                for raw in reaction_evidence_payload.get("sources", []):
                    item = dict(raw)
                    item["path"] = _resolve_path(item.get("path"), base_dir=base_dir)
                    resolved_sources.append(item)
                reaction_evidence_payload["sources"] = resolved_sources
            bootstrap_payload["reaction_evidence"] = reaction_evidence_payload

        normalized["bootstrap"] = bootstrap_payload
    return normalized


def _load_config_payload(path: str | Path, *, stack: Optional[List[str]] = None) -> tuple[Dict[str, Any], List[str]]:
    config_path = Path(path).resolve()
    marker = str(config_path)
    current_stack = list(stack or [])
    if marker in current_stack:
        cycle = " -> ".join(current_stack + [marker])
        raise ValueError(f"config extends cycle detected: {cycle}")

    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    extends_value = payload.pop("extends", [])
    if isinstance(extends_value, str):
        extends_items = [extends_value]
    else:
        extends_items = list(extends_value or [])

    merged: Dict[str, Any] = {}
    sources: List[str] = []
    for raw_parent in extends_items:
        parent_path = _resolve_path(str(raw_parent), base_dir=config_path.parent)
        parent_payload, parent_sources = _load_config_payload(parent_path, stack=current_stack + [marker])
        merged = _deep_merge_payload(merged, parent_payload)
        sources.extend(parent_sources)

    normalized_payload = _normalize_payload_paths(payload, base_dir=config_path.parent)
    merged = _deep_merge_payload(merged, normalized_payload)
    sources.append(marker)
    return merged, _dedupe_preserve_order(sources)


def load_config(path: str | Path) -> BuildConfig:
    config_path = Path(path).resolve()
    payload, config_sources = _load_config_payload(config_path)
    base_dir = config_path.parent

    feeds = [FeedSpec(**entry) for entry in payload.get("feeds", [])]
    if not feeds:
        raise ValueError("config must include at least one feed species")

    bootstrap_payload = payload.get("bootstrap", {})
    pubchem = PubChemOptions(**bootstrap_payload.get("pubchem", {}))
    pubchem.snapshot_path = _resolve_path(pubchem.snapshot_path, base_dir=base_dir)

    nist_asd = NistAsdOptions(**bootstrap_payload.get("nist_asd", {}))
    nist_asd.export_paths = _resolve_paths(nist_asd.export_paths, base_dir=base_dir)

    atct = AtctOptions(**bootstrap_payload.get("atct", {}))
    atct.snapshot_path = _resolve_path(atct.snapshot_path, base_dir=base_dir)

    reaction_evidence_payload = dict(bootstrap_payload.get("reaction_evidence", {}))
    source_specs = _resolve_source_specs(list(reaction_evidence_payload.get("sources", [])), base_dir=base_dir)

    reaction_evidence = ReactionEvidenceOptions(
        sources=source_specs,
        seed_templates=bool(reaction_evidence_payload.get("seed_templates", True)),
        max_templates_per_source=int(reaction_evidence_payload.get("max_templates_per_source", 60)),
        require_reactant_overlap=bool(reaction_evidence_payload.get("require_reactant_overlap", True)),
    )
    state_master_specs = _resolve_state_master_specs(list(payload.get("state_masters", [])), base_dir=base_dir)
    state_promotions_payload = dict(payload.get("state_promotions", {}))
    template_promotions_payload = dict(payload.get("template_promotions", {}))

    config = BuildConfig(
        feeds=feeds,
        projectiles=list(payload.get("projectiles", ["e-"])),
        libraries=list(payload.get("libraries", ["ch4", "c_c4f8"])),
        catalog_paths=_resolve_paths(list(payload.get("catalog_paths", [])), base_dir=base_dir),
        catalog_policy=CatalogPolicyOptions(**payload.get("catalog_policy", {})),
        state_masters=state_master_specs,
        state_filters=StateFilterOptions(**payload.get("state_filters", {})),
        state_promotions=StatePromotionOptions(
            molecular_excited_states=MolecularExcitedStatePromotionOptions(
                **state_promotions_payload.get("molecular_excited_states", {})
            )
        ),
        template_promotions=TemplatePromotionOptions(
            source_backed_templates=SourceBackedTemplatePromotionOptions(
                **template_promotions_payload.get("source_backed_templates", {})
            ),
            molecular_excited_state_templates=MolecularExcitedStateTemplatePromotionOptions(
                **template_promotions_payload.get("molecular_excited_state_templates", {})
            ),
        ),
        limits=Limits(**payload.get("limits", {})),
        conditions=Conditions(**payload.get("conditions", {})),
        bootstrap=BootstrapOptions(
            pubchem=pubchem,
            nist_asd=nist_asd,
            atct=atct,
            reaction_evidence=reaction_evidence,
        ),
        alias_path=_resolve_path(payload.get("alias_path"), base_dir=base_dir),
        excited_state_registry_path=_resolve_path(payload.get("excited_state_registry_path"), base_dir=base_dir),
        source_profiles_path=_resolve_path(payload.get("source_profiles_path"), base_dir=base_dir),
        config_path=str(config_path),
        config_sources=config_sources,
    )
    return config
