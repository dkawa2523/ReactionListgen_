from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional

from .adapters import (
    AtctSnapshotAdapter,
    NistAsdBootstrapAdapter,
    PubChemIdentityAdapter,
    ReactionEvidenceAggregator,
    ReactionEvidenceFactory,
    ReactionEvidenceIndex,
    ReactionEvidencePlanner,
)
from .builder import NetworkBuilder
from .catalog import TemplateCatalog
from .config import BuildConfig, EvidenceSourceSpec, load_config
from .excited_template_promotion import promote_molecular_excited_state_templates
from .excited_state_registry import ExcitedStateRegistry
from .normalization import AliasResolver
from .source_profiles import SourceStrengthRegistry
from .state_catalog import load_state_master, materialize_state_master
from .state_promotion import promote_molecular_excited_states
from .template_promotion import promote_source_backed_templates


@dataclass(slots=True)
class AppRuntime:
    config: BuildConfig
    catalog: TemplateCatalog
    alias_resolver: AliasResolver
    strength_registry: SourceStrengthRegistry
    indexes: List[ReactionEvidenceIndex] = field(default_factory=list)
    excited_state_registry: ExcitedStateRegistry = field(default_factory=ExcitedStateRegistry.empty)
    pubchem: Optional[PubChemIdentityAdapter] = None
    asd: Optional[NistAsdBootstrapAdapter] = None
    atct: Optional[AtctSnapshotAdapter] = None

    def build_network_builder(self) -> NetworkBuilder:
        evidence_aggregator = None
        evidence_planner = None
        if self.indexes:
            evidence_aggregator = ReactionEvidenceAggregator(
                self.indexes,
                alias_resolver=self.alias_resolver,
            )
            evidence_planner = ReactionEvidencePlanner(
                indexes=self.indexes,
                alias_resolver=self.alias_resolver,
            )
        return NetworkBuilder(
            config=self.config,
            catalog=self.catalog,
            pubchem=self.pubchem,
            asd=self.asd,
            atct=self.atct,
            evidence_aggregator=evidence_aggregator,
            evidence_planner=evidence_planner,
        )


def _refresh_alias_resolver(
    catalog: TemplateCatalog,
    *,
    config: BuildConfig,
    excited_state_registry: ExcitedStateRegistry,
) -> AliasResolver:
    return AliasResolver.from_catalog(
        catalog,
        alias_path=config.alias_path,
        excited_state_registry=excited_state_registry,
    )


def _merge_promoted_templates(
    catalog: TemplateCatalog,
    templates: List,
    *,
    config: BuildConfig,
    resource_name: str,
) -> None:
    if not templates:
        return
    catalog.merge_templates(
        templates,
        equation_conflict_policy=config.catalog_policy.reaction_conflict_policy,
        merge_reason=resource_name,
    )
    catalog.loaded_resources.append(resource_name)


def build_runtime(
    config_or_path: BuildConfig | str | Path,
    *,
    include_evidence_indexes: bool = True,
) -> AppRuntime:
    config = _load_config(config_or_path)
    asd = _build_asd_adapter(config)
    catalog = build_catalog(config, asd=asd)
    excited_state_registry = ExcitedStateRegistry.from_path(config.excited_state_registry_path)
    alias_resolver = _refresh_alias_resolver(
        catalog,
        config=config,
        excited_state_registry=excited_state_registry,
    )
    strength_registry = SourceStrengthRegistry.from_path(config.source_profiles_path)
    promotion_enabled = config.state_promotions.molecular_excited_states.enabled
    template_promotion_enabled = config.template_promotions.source_backed_templates.enabled
    excited_template_promotion_enabled = config.template_promotions.molecular_excited_state_templates.enabled
    state_master_entries = (
        _load_state_master_entries(config)
        if (promotion_enabled or template_promotion_enabled or excited_template_promotion_enabled)
        else []
    )
    built_indexes = _build_evidence_indexes(
        config.bootstrap.reaction_evidence.sources,
        alias_resolver=alias_resolver,
        strength_registry=strength_registry,
        feed_formulas=[feed.formula for feed in config.feeds],
    ) if (include_evidence_indexes or promotion_enabled or template_promotion_enabled or excited_template_promotion_enabled) else []
    if promotion_enabled and built_indexes:
        promoted_species = promote_molecular_excited_states(
            state_master_entries=state_master_entries,
            indexes=built_indexes,
            existing_species=catalog.species_library,
            options=config.state_promotions.molecular_excited_states,
            excited_state_registry=excited_state_registry,
        )
        if promoted_species:
            catalog.merge_species(promoted_species)
            catalog.loaded_resources.append("state_promotion:molecular_excited_states")
            alias_resolver = _refresh_alias_resolver(
                catalog,
                config=config,
                excited_state_registry=excited_state_registry,
            )
    if template_promotion_enabled and built_indexes:
        promoted_templates = promote_source_backed_templates(
            state_master_entries=state_master_entries,
            indexes=built_indexes,
            existing_species=catalog.species_library,
            existing_templates=catalog.templates,
            options=config.template_promotions.source_backed_templates,
        )
        _merge_promoted_templates(
            catalog,
            promoted_templates,
            config=config,
            resource_name="template_promotion:source_backed_templates",
        )
    if excited_template_promotion_enabled:
        excited_templates = promote_molecular_excited_state_templates(
            state_master_entries=state_master_entries,
            existing_species=catalog.species_library,
            existing_templates=catalog.templates,
            options=config.template_promotions.molecular_excited_state_templates,
        )
        _merge_promoted_templates(
            catalog,
            excited_templates,
            config=config,
            resource_name="template_promotion:molecular_excited_state_templates",
        )
    indexes = built_indexes if include_evidence_indexes else []

    pubchem = None
    if config.bootstrap.pubchem.enabled:
        pubchem = PubChemIdentityAdapter(
            snapshot_path=config.bootstrap.pubchem.snapshot_path,
            live_api=config.bootstrap.pubchem.live_api,
        )
    atct = None
    if config.bootstrap.atct.enabled and config.bootstrap.atct.snapshot_path:
        atct = AtctSnapshotAdapter(config.bootstrap.atct.snapshot_path)

    return AppRuntime(
        config=config,
        catalog=catalog,
        alias_resolver=alias_resolver,
        strength_registry=strength_registry,
        indexes=indexes,
        excited_state_registry=excited_state_registry,
        pubchem=pubchem,
        asd=asd,
        atct=atct,
    )

def build_catalog(
    config: BuildConfig,
    *,
    asd: Optional[NistAsdBootstrapAdapter] = None,
) -> TemplateCatalog:
    catalog = TemplateCatalog.from_sources(
        config.libraries,
        config.catalog_paths,
        charge_window_min=config.state_filters.charge_window_min,
        charge_window_max=config.state_filters.charge_window_max,
    )
    asd_adapter = asd or _build_asd_adapter(config)
    for spec in config.state_masters:
        entries = load_state_master(spec.path)
        prototypes = materialize_state_master(
            entries,
            families=spec.families or None,
            charge_window_min=config.state_filters.charge_window_min,
            charge_window_max=config.state_filters.charge_window_max,
            include_disabled=spec.include_disabled,
            asd=asd_adapter,
            asd_max_ion_charge=config.bootstrap.nist_asd.max_ion_charge,
            asd_max_levels_per_spectrum=config.bootstrap.nist_asd.max_levels_per_spectrum,
        )
        catalog.merge_species(prototypes)
        descriptor = f"state_master:{spec.path}"
        if spec.families:
            descriptor += f"?families={','.join(spec.families)}"
        if asd_adapter:
            descriptor += "&source=asd" if "?" in descriptor else "?source=asd"
        catalog.loaded_resources.append(descriptor)
    return catalog


def _load_config(config_or_path: BuildConfig | str | Path) -> BuildConfig:
    if isinstance(config_or_path, BuildConfig):
        return config_or_path
    return load_config(config_or_path)


def _build_asd_adapter(config: BuildConfig) -> Optional[NistAsdBootstrapAdapter]:
    if not config.bootstrap.nist_asd.enabled or not config.bootstrap.nist_asd.export_paths:
        return None
    return NistAsdBootstrapAdapter(config.bootstrap.nist_asd.export_paths)


def _load_state_master_entries(config: BuildConfig):
    entries = []
    for spec in config.state_masters:
        for entry in load_state_master(spec.path):
            if spec.families and entry.family.lower() not in {name.lower() for name in spec.families}:
                continue
            if not spec.include_disabled and not entry.enabled:
                continue
            entries.append(entry)
    return entries


def _build_evidence_indexes(
    specs: Iterable[EvidenceSourceSpec],
    *,
    alias_resolver: AliasResolver,
    strength_registry: SourceStrengthRegistry,
    feed_formulas: Iterable[str],
) -> List[ReactionEvidenceIndex]:
    factory = ReactionEvidenceFactory(
        alias_resolver=alias_resolver,
        strength_registry=strength_registry,
    )
    return factory.build_indexes(specs, feed_formulas=feed_formulas)
