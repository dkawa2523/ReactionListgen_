from __future__ import annotations

from typing import Dict, List, Optional, Set

from .adapters import AtctSnapshotAdapter, NistAsdBootstrapAdapter, PubChemIdentityAdapter, ReactionEvidenceAggregator, ReactionEvidencePlanner
from .balancing import BalanceResolver
from .catalog import TemplateCatalog
from .config import BuildConfig, FeedSpec
from .formula import parse_species_token
from .model import BuildResult, DiagnosticEntry, ReactionRecord, SpeciesState
from .network_manifest import build_result_network_manifest
from .provenance import EvidenceRecord
from .scoring import score_reaction, score_species


NON_EXTERNAL_REACTION_EVIDENCE_SYSTEMS = {
    "atct",
    "catalog",
    "inference",
    "pubchem",
    "template_library",
}


class NetworkBuilder:
    def __init__(
        self,
        *,
        config: BuildConfig,
        catalog: TemplateCatalog,
        pubchem: Optional[PubChemIdentityAdapter] = None,
        asd: Optional[NistAsdBootstrapAdapter] = None,
        atct: Optional[AtctSnapshotAdapter] = None,
        evidence_aggregator: Optional[ReactionEvidenceAggregator] = None,
        evidence_planner: Optional[ReactionEvidencePlanner] = None,
    ) -> None:
        self.config = config
        self.catalog = catalog
        self.pubchem = pubchem
        self.asd = asd
        self.atct = atct
        self.evidence_aggregator = evidence_aggregator
        self.evidence_planner = evidence_planner
        self.balance_resolver = BalanceResolver(catalog)
        self.states_by_key: Dict[str, SpeciesState] = {}
        self.reactions_by_key: Dict[str, ReactionRecord] = {}
        self.templates_by_key = {template.key: template for template in catalog.templates}
        self.feed_keys = {feed.species_key for feed in config.feeds}
        self.diagnostics: List[DiagnosticEntry] = []
        self.asd_bootstrap_keys: Set[str] = set()

    def _record(self, level: str, code: str, message: str, **context: object) -> None:
        self.diagnostics.append(DiagnosticEntry(level=level, code=code, message=message, context=dict(context)))

    def _apply_asd_bootstrap(self) -> None:
        if not self.asd:
            return
        formulas = [feed.formula for feed in self.config.feeds]
        prototypes = [
            prototype
            for prototype in self.asd.bootstrap(
                formulas,
                max_ion_charge=self.config.bootstrap.nist_asd.max_ion_charge,
                max_levels_per_spectrum=self.config.bootstrap.nist_asd.max_levels_per_spectrum,
            )
            if self.config.state_filters.allows_charge(prototype.charge)
        ]
        added = self.catalog.merge_species(prototypes)
        self.asd_bootstrap_keys = {proto.key for proto in prototypes}
        self._record("info", "asd_bootstrap", "Merged ASD-derived atomic states into catalog.", added_species=added)

    def _seed_external_templates(self) -> None:
        if not self.evidence_planner or not self.config.bootstrap.reaction_evidence.seed_templates:
            return
        known_tokens: Set[str] = set(self.feed_keys)
        known_tokens.update(feed.formula for feed in self.config.feeds)
        for proto in self.catalog.species_library.values():
            known_tokens.add(proto.key)
            known_tokens.add(proto.formula)
        templates, counts = self.evidence_planner.seed_templates(
            known_tokens=known_tokens,
            max_templates_per_source=self.config.bootstrap.reaction_evidence.max_templates_per_source,
            require_reactant_overlap=self.config.bootstrap.reaction_evidence.require_reactant_overlap,
        )
        merge_stats = self.catalog.merge_templates(
            templates,
            equation_conflict_policy=self.config.catalog_policy.reaction_conflict_policy,
            merge_reason="external_seed",
        )
        if merge_stats.added or merge_stats.replaced:
            self.templates_by_key = {template.key: template for template in self.catalog.templates}
        self._record(
            "info",
            "external_templates_seeded",
            "Merged external evidence-derived templates into catalog.",
            merge_stats=merge_stats.as_dict(),
            by_source=counts,
        )

    def _generic_state(self, key: str, generation: int) -> SpeciesState:
        parsed = parse_species_token(key)
        state = SpeciesState(
            prototype_key=parsed.normalized_label,
            display_name=parsed.normalized_label,
            formula=parsed.formula or parsed.normalized_label,
            charge=parsed.charge,
            state_class=parsed.state_class,
            generation=generation,
            excitation_label=parsed.excitation_label,
            excitation_energy_ev=parsed.excitation_energy_ev,
            tags=[parsed.state_class],
            metadata={},
            evidence=[
                EvidenceRecord(
                    source_system="inference",
                    source_name="token_parser",
                    acquisition_method="package_template",
                    evidence_kind="parser_event",
                    support_score=0.35,
                    locator=key,
                    note="State synthesized from token because no catalog prototype existed.",
                )
            ],
        )
        self._record("warning", "generic_state", f"Generic state synthesized for {key}", species_key=key)
        return state

    def _state_from_prototype(self, key: str, generation: int) -> SpeciesState:
        proto = self.catalog.get_species(key)
        if not proto:
            return self._generic_state(key, generation)
        origin = str(proto.metadata.get("state_origin") or "catalog_species")
        source_name = str(proto.metadata.get("catalog_resource") or origin)
        return SpeciesState(
            prototype_key=proto.key,
            display_name=proto.display_name,
            formula=proto.formula,
            charge=proto.charge,
            state_class=proto.state_class,
            generation=generation,
            multiplicity=proto.multiplicity,
            structure_id=proto.structure_id,
            excitation_label=proto.excitation_label,
            excitation_energy_ev=proto.excitation_energy_ev,
            tags=list(proto.tags),
            metadata=dict(proto.metadata),
            evidence=[
                EvidenceRecord(
                    source_system="catalog",
                    source_name=source_name,
                    acquisition_method="package_template",
                    evidence_kind="curated_species_record",
                    support_score=0.70,
                    locator=proto.key,
                    note=f"Species instantiated from {origin}.",
                )
            ],
        )

    def _enrich_feed_identity(self, state: SpeciesState, feed: FeedSpec) -> None:
        if not self.pubchem:
            return
        query = feed.identity_query or feed.display_name or feed.formula
        namespace = feed.identity_namespace
        record = self.pubchem.resolve(query=query, namespace=namespace)
        if not record:
            self._record("warning", "identity_missing", f"No PubChem identity record found for {feed.species_key}", species_key=feed.species_key, query=query)
            return
        state.identity = record
        state.evidence.append(
            EvidenceRecord(
                source_system="pubchem",
                source_name="PubChem",
                acquisition_method="api_lookup" if self.config.bootstrap.pubchem.live_api else "offline_snapshot",
                evidence_kind="identity_database_record",
                support_score=0.88 if not record.ambiguous else 0.65,
                source_url=record.source_url,
                locator=str(record.cid) if record.cid is not None else query,
                citation="PubChem compound identity record",
                note="Feed identity canonicalized with PubChem." if not record.ambiguous else "Ambiguous PubChem lookup; selected first candidate.",
            )
        )
        if record.ambiguous:
            self._record(
                "warning",
                "identity_ambiguous",
                f"PubChem lookup for {feed.species_key} returned multiple candidates.",
                species_key=feed.species_key,
                query=query,
                namespace=namespace,
                candidate_count=record.candidate_count,
            )

    def _enrich_thermo(self, state: SpeciesState) -> None:
        if self.atct:
            self.atct.enrich_species(state)

    def _ensure_state(self, key: str, generation: int) -> SpeciesState:
        existing = self.states_by_key.get(key)
        if existing:
            if generation < existing.generation:
                existing.generation = generation
            return existing
        state = self._state_from_prototype(key, generation)
        self._enrich_thermo(state)
        state.confidence = score_species(state)
        self.states_by_key[key] = state
        return state

    def _seed_states(self) -> None:
        for feed in self.config.feeds:
            if not self._key_within_charge_window(feed.species_key):
                self._record(
                    "warning",
                    "feed_charge_filtered",
                    f"Feed {feed.species_key} skipped by charge window.",
                    species_key=feed.species_key,
                )
                continue
            state = self._ensure_state(feed.species_key, generation=0)
            self._enrich_feed_identity(state, feed)
            state.confidence = score_species(state)

        for bootstrap_key in sorted(self.asd_bootstrap_keys):
            state = self._ensure_state(bootstrap_key, generation=0)
            state.confidence = score_species(state)

        for projectile in self.config.projectiles:
            if projectile == "e-":
                continue
            if not self._key_within_charge_window(projectile):
                self._record(
                    "warning",
                    "projectile_charge_filtered",
                    f"Projectile {projectile} skipped by charge window.",
                    projectile=projectile,
                )
                continue
            self._ensure_state(projectile, generation=0)

    def _template_applicable(self, template_key: str, frontier: Set[str], available: Set[str]) -> bool:
        template = self.templates_by_key[template_key]
        if template.required_projectile and template.required_projectile not in self.config.projectiles:
            return False
        if not self._template_within_charge_window(template):
            return False
        if not set(template.reactants).issubset(available):
            return False
        if not frontier.intersection(template.reactants):
            return False
        return True

    def _apply_template(self, template_key: str, generation: int) -> Optional[ReactionRecord]:
        template = self.templates_by_key[template_key]
        resolved = self.balance_resolver.resolve(template)
        self.diagnostics.extend(resolved.diagnostics)
        template = resolved.template
        self.templates_by_key[template.key] = template
        if not self._template_within_charge_window(template):
            self._record(
                "info",
                "template_charge_filtered",
                f"Template {template.key} skipped by charge window.",
                template_key=template.key,
            )
            return None
        reactant_states = [self._ensure_state(key, generation=max(0, generation - 1)) for key in template.reactants]
        product_states = [self._ensure_state(key, generation=generation) for key in template.products]
        reaction = ReactionRecord(
            key=template.key,
            family=template.family,
            equation=template.equation(),
            reactant_state_ids=[state.id for state in reactant_states],
            product_state_ids=[state.id for state in product_states],
            reactant_keys=list(template.reactants),
            product_keys=list(template.products),
            lhs_tokens=list(template.lhs_tokens),
            rhs_tokens=list(template.rhs_tokens),
            generation=generation,
            threshold_ev=template.threshold_ev,
            delta_h_kj_mol=template.delta_h_kj_mol,
            evidence=list(template.evidence),
            note=template.note,
            metadata=dict(template.metadata),
        )
        if reaction.dedupe_key() in self.reactions_by_key:
            return None
        self.reactions_by_key[reaction.dedupe_key()] = reaction
        reaction.confidence = score_reaction(
            template=template,
            reaction=reaction,
            generation=generation,
            electron_max_ev=self.config.conditions.electron_max_ev,
            ion_max_ev=self.config.conditions.ion_max_ev,
        )
        for state in product_states:
            state.confidence = score_species(state, parent_reaction=reaction)
        return reaction

    def _annotate_reactions(self) -> None:
        states_by_id = {state.id: state for state in self.states_by_key.values()}
        to_remove: Set[str] = set()
        for dedupe_key, reaction in list(self.reactions_by_key.items()):
            template = self.templates_by_key[reaction.key]
            if self.atct and reaction.delta_h_kj_mol is None:
                reaction.delta_h_kj_mol = self.atct.reaction_delta_h(reaction, states_by_id)
                if reaction.delta_h_kj_mol is not None:
                    reaction.evidence.append(
                        EvidenceRecord(
                            source_system="atct",
                            source_name="Active Thermochemical Tables",
                            acquisition_method="offline_snapshot",
                            evidence_kind="reaction_enthalpy_inference",
                            support_score=0.88,
                            locator=reaction.key,
                            citation="ATcT-derived reaction enthalpy from species enthalpies",
                            note="Reaction enthalpy computed from attached species thermochemistry.",
                        )
                    )

            if self.evidence_aggregator:
                reaction.evidence.extend(self.evidence_aggregator.match(reaction))

            hard_limit = self.config.bootstrap.atct.hard_endothermic_kj_mol
            prunable = template.family in set(self.config.bootstrap.atct.prunable_families)
            external_hits = self._has_external_reaction_support(reaction.evidence)
            if prunable and reaction.delta_h_kj_mol is not None and reaction.delta_h_kj_mol > hard_limit and not external_hits:
                to_remove.add(dedupe_key)
                self._record(
                    "info",
                    "thermochem_pruned",
                    f"Pruned strongly endothermic reaction {reaction.key}",
                    reaction_key=reaction.key,
                    delta_h_kj_mol=reaction.delta_h_kj_mol,
                    hard_limit_kj_mol=hard_limit,
                )
                continue

            reaction.confidence = score_reaction(
                template=template,
                reaction=reaction,
                generation=reaction.generation,
                electron_max_ev=self.config.conditions.electron_max_ev,
                ion_max_ev=self.config.conditions.ion_max_ev,
            )

        for key in to_remove:
            self.reactions_by_key.pop(key, None)

    def _has_external_reaction_support(self, evidence: List[EvidenceRecord]) -> bool:
        for record in evidence:
            if record.source_system in NON_EXTERNAL_REACTION_EVIDENCE_SYSTEMS:
                continue
            if record.acquisition_method == "package_template":
                continue
            return True
        return False

    def _key_within_charge_window(self, key: str) -> bool:
        charge = parse_species_token(key).charge
        return self.config.state_filters.allows_charge(charge)

    def _template_within_charge_window(self, template) -> bool:
        for key in list(template.reactants) + list(template.products):
            if not self._key_within_charge_window(key):
                return False
        return True

    def _cleanup_species(self) -> None:
        used = set(self.feed_keys)
        for reaction in self.reactions_by_key.values():
            used.update(reaction.reactant_keys)
            used.update(reaction.product_keys)
        used.update(key for key, state in self.states_by_key.items() if "asd_bootstrap" in state.tags)
        self.states_by_key = {key: state for key, state in self.states_by_key.items() if key in used}

    def build(self) -> BuildResult:
        self._apply_asd_bootstrap()
        self._seed_external_templates()
        self._seed_states()
        available = set(self.states_by_key.keys())
        frontier = {state.prototype_key for state in self.states_by_key.values() if state.generation == 0}

        for generation in range(1, self.config.limits.max_generation + 1):
            newly_created: Set[str] = set()
            candidate_keys = [key for key in self.templates_by_key if self._template_applicable(key, frontier, available)]
            for template_key in candidate_keys:
                reaction = self._apply_template(template_key, generation)
                if not reaction:
                    continue
                for key in reaction.product_keys:
                    if key not in available:
                        newly_created.add(key)
                available.update(reaction.product_keys)
            if not newly_created:
                break
            ordered = sorted(
                (self.states_by_key[key] for key in newly_created if key in self.states_by_key),
                key=lambda state: (state.confidence.final_score if state.confidence else 0.0, state.prototype_key),
                reverse=True,
            )[: self.config.limits.beam_width]
            frontier = {state.prototype_key for state in ordered}
            if len(self.states_by_key) >= self.config.limits.max_species:
                self._record("warning", "max_species_reached", "Build stopped because max_species limit was reached.", max_species=self.config.limits.max_species)
                break

        self._annotate_reactions()
        self._cleanup_species()
        metadata = {
            "feed_count": len(self.config.feeds),
            "species_count": len(self.states_by_key),
            "reaction_count": len(self.reactions_by_key),
            "loaded_resources": list(self.catalog.loaded_resources),
            "catalog_policy": self.config.catalog_policy.as_dict(),
            "config_sources": list(self.config.config_sources),
        }
        result = BuildResult(
            species=sorted(self.states_by_key.values(), key=lambda state: (state.generation, state.prototype_key)),
            reactions=sorted(self.reactions_by_key.values(), key=lambda reaction: (reaction.generation, reaction.key)),
            diagnostics=list(self.diagnostics),
            metadata=metadata,
        )
        result.metadata["network_manifest"] = build_result_network_manifest(result)
        return result
