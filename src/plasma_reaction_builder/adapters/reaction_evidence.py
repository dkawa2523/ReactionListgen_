from __future__ import annotations

from typing import Callable, Dict, Iterable, List, Optional

from ..config import EvidenceSourceSpec
from ..formula import parse_species_token
from ..model import ReactionRecord
from ..normalization import AliasResolver
from ..provenance import EvidenceRecord
from ..source_profiles import SourceStrengthRegistry
from .evidence_common import ExternalEvidenceTemplateSeeder, ReactionEvidenceEntry, ReactionEvidenceIndex
from .http import SimpleHttpClient
from .kida import KidaNetworkIndex
from .nist_kinetics import NistKineticsIndex
from .qdb_evidence import QdbEvidenceIndex
from .umist import UmistRate22Index
from .vamdc import VamdcTapClient, VamdcXsamsIndex


class ReactionEvidenceAggregator:
    def __init__(self, indexes: Iterable[ReactionEvidenceIndex], *, alias_resolver: Optional[AliasResolver] = None) -> None:
        self.indexes = list(indexes)
        self.alias_resolver = alias_resolver or AliasResolver.empty()

    def match(self, reaction: ReactionRecord) -> List[EvidenceRecord]:
        lhs_tokens = self.alias_resolver.canonicalize_tokens(reaction.lhs_tokens)
        rhs_tokens = self.alias_resolver.canonicalize_tokens(reaction.rhs_tokens)
        matches: List[EvidenceRecord] = []
        for index in self.indexes:
            matches.extend(index.match_tokens(lhs_tokens, rhs_tokens))
        unique = {}
        for record in matches:
            key = (record.source_system, record.source_name, record.note or "", record.citation or "")
            unique[key] = record
        return list(unique.values())


class ReactionEvidenceFactory:
    def __init__(
        self,
        *,
        http: Optional[SimpleHttpClient] = None,
        alias_resolver: Optional[AliasResolver] = None,
        strength_registry: Optional[SourceStrengthRegistry] = None,
    ) -> None:
        self.http = http or SimpleHttpClient()
        self.alias_resolver = alias_resolver or AliasResolver.empty()
        self.strength_registry = strength_registry or SourceStrengthRegistry.from_path(None)
        self._loaders: Dict[str, Callable[[EvidenceSourceSpec, List[str]], Optional[ReactionEvidenceIndex]]] = {
            "nist_kinetics_snapshot": self._load_nist_kinetics_snapshot,
            "qdb_snapshot": self._load_qdb_snapshot,
            "umist_ratefile": self._load_umist_ratefile,
            "kida_network": self._load_kida_network,
            "vamdc_xsams": self._load_vamdc_xsams,
            "vamdc_live": self._load_vamdc_live,
        }

    def build_indexes(self, specs: Iterable[EvidenceSourceSpec], *, feed_formulas: Optional[Iterable[str]] = None) -> List[ReactionEvidenceIndex]:
        feed_formula_list = sorted({formula for formula in (feed_formulas or []) if formula})
        indexes: List[ReactionEvidenceIndex] = []
        for spec in specs:
            if not spec.enabled:
                continue
            kind = spec.kind.lower()
            loader = self._loaders.get(kind)
            if loader is None:
                raise ValueError(f"Unsupported evidence source kind: {spec.kind}")
            index = loader(spec, feed_formula_list)
            if index is not None:
                indexes.append(self._normalize_index(index))
        return indexes

    def _normalize_index(self, index: ReactionEvidenceIndex) -> ReactionEvidenceIndex:
        normalized: List[ReactionEvidenceEntry] = []
        for entry in index.entries:
            source_key = entry.source_system or index.source_id
            profile = self.strength_registry.profile_for(source_key)
            metadata = dict(entry.metadata)
            if profile is not None:
                metadata.setdefault("source_family", profile.family)
                metadata.setdefault("source_priority", profile.priority)
            normalized.append(
                ReactionEvidenceEntry(
                    source_system=entry.source_system,
                    source_name=entry.source_name,
                    reactants=self.alias_resolver.canonicalize_tokens(
                        entry.reactants,
                        source_system=entry.source_system,
                    ),
                    products=self.alias_resolver.canonicalize_tokens(
                        entry.products,
                        source_system=entry.source_system,
                    ),
                    citation=entry.citation,
                    source_url=entry.source_url,
                    support_score=self.strength_registry.apply(source_key, entry.support_score),
                    note=entry.note,
                    metadata=self._normalize_entry_metadata(metadata, source_system=entry.source_system),
                    acquisition_method=entry.acquisition_method,
                    evidence_kind=entry.evidence_kind,
                )
            )
        return ReactionEvidenceIndex(normalized, source_id=index.source_id)

    def _load_nist_kinetics_snapshot(self, spec: EvidenceSourceSpec, feed_formulas: List[str]) -> Optional[ReactionEvidenceIndex]:
        if not spec.path:
            return None
        return NistKineticsIndex.from_json(spec.path)

    def _load_qdb_snapshot(self, spec: EvidenceSourceSpec, feed_formulas: List[str]) -> Optional[ReactionEvidenceIndex]:
        if not spec.path:
            return None
        return QdbEvidenceIndex.from_json(spec.path)

    def _load_umist_ratefile(self, spec: EvidenceSourceSpec, feed_formulas: List[str]) -> Optional[ReactionEvidenceIndex]:
        if not spec.path:
            return None
        return UmistRate22Index.from_ratefile(spec.path, include_special_processes=spec.include_special_processes)

    def _load_kida_network(self, spec: EvidenceSourceSpec, feed_formulas: List[str]) -> Optional[ReactionEvidenceIndex]:
        if not spec.path:
            return None
        return KidaNetworkIndex.from_file(spec.path, include_special_processes=spec.include_special_processes)

    def _load_vamdc_xsams(self, spec: EvidenceSourceSpec, feed_formulas: List[str]) -> Optional[ReactionEvidenceIndex]:
        if not spec.path:
            return None
        return VamdcXsamsIndex.from_path(
            spec.path,
            source_name=spec.source_name or "VAMDC XSAMS",
            source_system=spec.source_system or "vamdc",
            support_score=spec.support_score,
            source_url=spec.url,
        )

    def _load_vamdc_live(self, spec: EvidenceSourceSpec, feed_formulas: List[str]) -> Optional[ReactionEvidenceIndex]:
        if not spec.url:
            return None
        queries = self.expand_vamdc_queries(spec, feed_formulas=feed_formulas)
        if not queries:
            return None
        client = VamdcTapClient(http=self.http)
        return client.collect_index(
            url=spec.url,
            queries=queries,
            source_name=spec.source_name or "VAMDC live node",
            source_system=spec.source_system or "vamdc",
            support_score=spec.support_score,
        )

    @staticmethod
    def expand_vamdc_queries(spec: EvidenceSourceSpec, *, feed_formulas: Iterable[str]) -> List[str]:
        if spec.query:
            return [spec.query]
        if spec.queries:
            return list(spec.queries)
        formulas: List[str] = []
        if spec.species_queries:
            formulas = [formula for formula in spec.species_queries if formula]
        elif spec.use_feed_formulas:
            formulas = [formula for formula in feed_formulas if formula]
        if formulas:
            template = spec.query_template or "SELECT * WHERE MoleculeStoichiometricFormula = '{formula}'"
            return [template.format(formula=formula) for formula in formulas]
        return []

    @staticmethod
    def _expand_vamdc_queries(spec: EvidenceSourceSpec, *, feed_formulas: Iterable[str]) -> List[str]:
        return ReactionEvidenceFactory.expand_vamdc_queries(spec, feed_formulas=feed_formulas)

    def _normalize_entry_metadata(self, metadata: Dict[str, object], *, source_system: str) -> Dict[str, object]:
        raw_specs = metadata.get("promoted_excited_states")
        if isinstance(raw_specs, dict):
            raw_specs = [raw_specs]
        if not isinstance(raw_specs, list):
            return metadata
        normalized_specs = []
        for raw in raw_specs:
            if not isinstance(raw, dict):
                normalized_specs.append(raw)
                continue
            item = dict(raw)
            token = item.get("token")
            if token:
                item["token"] = self.alias_resolver.canonicalize_token(
                    str(token),
                    source_system=source_system,
                )
            normalized_specs.append(item)
        normalized = dict(metadata)
        normalized["promoted_excited_states"] = normalized_specs
        return normalized


class ReactionEvidencePlanner:
    def __init__(self, *, indexes: Iterable[ReactionEvidenceIndex], alias_resolver: Optional[AliasResolver] = None) -> None:
        self.seeder = ExternalEvidenceTemplateSeeder(indexes)
        self.alias_resolver = alias_resolver or AliasResolver.empty()

    def seed_templates(self, *, known_tokens: Iterable[str], max_templates_per_source: int, require_reactant_overlap: bool):
        normalized = set()
        for token in known_tokens:
            canonical = self.alias_resolver.canonicalize_token(token)
            parsed = parse_species_token(canonical)
            if parsed.tracked:
                normalized.add(parsed.normalized_label)
                if parsed.formula:
                    normalized.add(parsed.formula)
        return self.seeder.seed_templates(
            known_tokens=normalized,
            max_templates_per_source=max_templates_per_source,
            require_reactant_overlap=require_reactant_overlap,
        )
