from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha1
from typing import Any, Dict, Iterable, List, Optional, Set

from ..formula import parse_species_token, tracked_signature
from ..scoring import is_balanced
from ..catalog import DEFAULT_EXTERNAL_SEED_TEMPLATE_PRIORITY
from ..model import ReactionTemplate
from ..provenance import EvidenceRecord


@dataclass(slots=True)
class ReactionEvidenceEntry:
    source_system: str
    source_name: str
    reactants: List[str]
    products: List[str]
    citation: Optional[str] = None
    source_url: Optional[str] = None
    support_score: float = 0.85
    note: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    acquisition_method: str = "offline_snapshot"
    evidence_kind: str = "direct_database_record"

    def forward_signature(self) -> tuple[tuple[str, ...], tuple[str, ...]]:
        return tracked_signature(self.reactants), tracked_signature(self.products)

    def reverse_signature(self) -> tuple[tuple[str, ...], tuple[str, ...]]:
        return tracked_signature(self.products), tracked_signature(self.reactants)

    def reactant_overlap_tokens(self) -> Set[str]:
        return _token_overlap_set(self.reactants)

    def all_overlap_tokens(self) -> Set[str]:
        return _token_overlap_set(self.reactants + self.products)

    def to_evidence_record(self, *, reverse: bool = False) -> EvidenceRecord:
        kind = self.evidence_kind if not reverse else f"reverse_{self.evidence_kind}"
        score = self.support_score if not reverse else max(0.45, self.support_score - 0.05)
        note = self.note or "Exact reaction match found in evidence source."
        if reverse:
            note = f"Reverse-direction match found in evidence source. {note}"
        return EvidenceRecord(
            source_system=self.source_system,
            source_name=self.source_name,
            acquisition_method=self.acquisition_method,
            evidence_kind=kind,
            support_score=score,
            source_url=self.source_url,
            citation=self.citation,
            note=note,
        )


class ReactionEvidenceIndex:
    def __init__(self, entries: Iterable[ReactionEvidenceEntry], *, source_id: Optional[str] = None) -> None:
        self.entries = list(entries)
        self.source_id = source_id or (self.entries[0].source_system if self.entries else "unknown")
        self.forward: Dict[tuple[tuple[str, ...], tuple[str, ...]], List[ReactionEvidenceEntry]] = {}
        self.reverse: Dict[tuple[tuple[str, ...], tuple[str, ...]], List[ReactionEvidenceEntry]] = {}
        self.by_reactant_overlap: Dict[str, List[ReactionEvidenceEntry]] = {}
        for entry in self.entries:
            self.forward.setdefault(entry.forward_signature(), []).append(entry)
            self.reverse.setdefault(entry.reverse_signature(), []).append(entry)
            for token in entry.reactant_overlap_tokens():
                self.by_reactant_overlap.setdefault(token, []).append(entry)

    def match_tokens(self, lhs_tokens: Iterable[str], rhs_tokens: Iterable[str]) -> List[EvidenceRecord]:
        signature = (tracked_signature(lhs_tokens), tracked_signature(rhs_tokens))
        matches: List[EvidenceRecord] = []
        for entry in self.forward.get(signature, []):
            matches.append(entry.to_evidence_record(reverse=False))
        for entry in self.reverse.get(signature, []):
            matches.append(entry.to_evidence_record(reverse=True))
        return matches

    def candidate_entries(self, known_tokens: Set[str], *, require_reactant_overlap: bool, limit: int) -> List[ReactionEvidenceEntry]:
        if limit <= 0:
            return []
        pool: List[ReactionEvidenceEntry] = []
        if require_reactant_overlap:
            seen: Set[int] = set()
            for token in known_tokens:
                for entry in self.by_reactant_overlap.get(token, []):
                    marker = id(entry)
                    if marker in seen:
                        continue
                    pool.append(entry)
                    seen.add(marker)
        else:
            pool = list(self.entries)
        pool.sort(key=lambda item: (-item.support_score, item.source_system, " + ".join(item.reactants), " + ".join(item.products)))
        return pool[:limit]


class ExternalEvidenceTemplateSeeder:
    def __init__(self, indexes: Iterable[ReactionEvidenceIndex]) -> None:
        self.indexes = list(indexes)

    def seed_templates(
        self,
        *,
        known_tokens: Set[str],
        max_templates_per_source: int,
        require_reactant_overlap: bool,
    ) -> tuple[List[ReactionTemplate], Dict[str, int]]:
        templates: List[ReactionTemplate] = []
        counts: Dict[str, int] = {}
        for index in self.indexes:
            entries = index.candidate_entries(
                known_tokens,
                require_reactant_overlap=require_reactant_overlap,
                limit=max_templates_per_source,
            )
            for entry in entries:
                template = evidence_entry_to_template(entry)
                if template is None:
                    continue
                templates.append(template)
                counts[index.source_id] = counts.get(index.source_id, 0) + 1
        unique = {template.key: template for template in templates}
        return list(unique.values()), counts


def evidence_entry_to_template(entry: ReactionEvidenceEntry) -> Optional[ReactionTemplate]:
    lhs_tokens = [token.strip() for token in entry.reactants if token and token.strip()]
    rhs_tokens = [token.strip() for token in entry.products if token and token.strip()]
    if not lhs_tokens or not rhs_tokens:
        return None

    tracked_reactants = [_tracked_key(token) for token in lhs_tokens]
    tracked_products = [_tracked_key(token) for token in rhs_tokens]
    required_projectile = None
    if any(parse_species_token(token).normalized_label == "e-" for token in lhs_tokens):
        required_projectile = "e-"
    reactants = [token for token in tracked_reactants if token]
    products = [token for token in tracked_products if token]
    if not reactants or not products:
        return None
    if not is_balanced(lhs_tokens, rhs_tokens):
        return None

    family = infer_family(lhs_tokens)
    key_material = entry.source_system + "|" + " + ".join(lhs_tokens) + " -> " + " + ".join(rhs_tokens)
    key = f"ext::{entry.source_system}::{sha1(key_material.encode('utf-8')).hexdigest()[:16]}"
    return ReactionTemplate(
        key=key,
        reactants=reactants,
        products=products,
        lhs_tokens=lhs_tokens,
        rhs_tokens=rhs_tokens,
        family=family,
        required_projectile=required_projectile,
        base_confidence=max(0.30, min(0.90, entry.support_score)),
        evidence=[entry.to_evidence_record(reverse=False)],
        note=entry.note or f"Seeded from {entry.source_name}",
        metadata={
            "template_origin": "external_seed",
            "template_layer": "seed",
            "template_priority": DEFAULT_EXTERNAL_SEED_TEMPLATE_PRIORITY,
            "template_source_system": entry.source_system,
            "template_source_name": entry.source_name,
            "source_support_score": entry.support_score,
            "source_url": entry.source_url,
        },
    )


def infer_family(lhs_tokens: Iterable[str]) -> str:
    parsed = [parse_species_token(token) for token in lhs_tokens]
    if any(token.normalized_label == "e-" for token in parsed):
        return "electron_collision_evidence"
    tracked = [token for token in parsed if token.tracked]
    if any(token.charge != 0 for token in tracked):
        if any(token.charge == 0 for token in tracked):
            return "ion_neutral_evidence"
        return "ion_ion_evidence"
    return "gas_phase_evidence"


def _tracked_key(token: str) -> Optional[str]:
    parsed = parse_species_token(token)
    if not parsed.tracked:
        return None
    return parsed.normalized_label


def _token_overlap_set(tokens: Iterable[str]) -> Set[str]:
    out: Set[str] = set()
    for token in tokens:
        parsed = parse_species_token(token)
        if not parsed.tracked:
            continue
        out.add(parsed.normalized_label)
        if parsed.formula:
            out.add(parsed.formula)
    return out
