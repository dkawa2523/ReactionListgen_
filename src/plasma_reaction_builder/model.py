from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import uuid

from .provenance import ConfidenceScore, EvidenceRecord


@dataclass(slots=True)
class IdentityRecord:
    query: str
    namespace: str
    cid: Optional[int] = None
    title: Optional[str] = None
    formula: Optional[str] = None
    molecular_weight: Optional[float] = None
    smiles: Optional[str] = None
    inchi: Optional[str] = None
    inchikey: Optional[str] = None
    synonyms: List[str] = field(default_factory=list)
    candidate_count: int = 0
    ambiguous: bool = False
    source_url: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Thermochemistry:
    delta_hf_298_kj_mol: Optional[float] = None
    delta_hf_0_kj_mol: Optional[float] = None
    source_version: Optional[str] = None
    doi: Optional[str] = None
    source_url: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SpeciesPrototype:
    key: str
    display_name: str
    formula: str
    charge: int = 0
    state_class: str = "ground"
    multiplicity: Optional[int] = None
    structure_id: Optional[str] = None
    excitation_label: Optional[str] = None
    excitation_energy_ev: Optional[float] = None
    nist_query: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SpeciesState:
    prototype_key: str
    display_name: str
    formula: str
    charge: int = 0
    state_class: str = "ground"
    generation: int = 0
    multiplicity: Optional[int] = None
    structure_id: Optional[str] = None
    excitation_label: Optional[str] = None
    excitation_energy_ev: Optional[float] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    identity: Optional[IdentityRecord] = None
    thermo: Thermochemistry = field(default_factory=Thermochemistry)
    evidence: List[EvidenceRecord] = field(default_factory=list)
    confidence: Optional[ConfidenceScore] = None
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def dedupe_key(self) -> str:
        return "|".join(
            [
                self.prototype_key,
                self.formula,
                str(self.charge),
                self.state_class,
                self.excitation_label or "",
            ]
        )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "prototype_key": self.prototype_key,
            "display_name": self.display_name,
            "formula": self.formula,
            "charge": self.charge,
            "state_class": self.state_class,
            "generation": self.generation,
            "multiplicity": self.multiplicity,
            "structure_id": self.structure_id,
            "excitation_label": self.excitation_label,
            "excitation_energy_ev": self.excitation_energy_ev,
            "tags": list(self.tags),
            "metadata": dict(self.metadata),
            "identity": self.identity.as_dict() if self.identity else None,
            "thermo": self.thermo.as_dict(),
            "evidence": [e.as_dict() for e in self.evidence],
            "confidence": self.confidence.as_dict() if self.confidence else None,
            "id": self.id,
        }


@dataclass(slots=True)
class MissingProductSpec:
    kind: str
    allowed_state_classes: List[str] = field(default_factory=list)
    allowed_tags: List[str] = field(default_factory=list)
    disallow_keys: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ReactionTemplate:
    key: str
    reactants: List[str]
    products: List[str]
    lhs_tokens: List[str]
    rhs_tokens: List[str]
    family: str
    required_projectile: Optional[str] = None
    threshold_ev: Optional[float] = None
    delta_h_kj_mol: Optional[float] = None
    base_confidence: float = 0.6
    evidence: List[EvidenceRecord] = field(default_factory=list)
    reference_ids: List[str] = field(default_factory=list)
    note: Optional[str] = None
    inferred_balance: bool = False
    missing_products: List[MissingProductSpec] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def equation(self) -> str:
        lhs = " + ".join(self.lhs_tokens) if self.lhs_tokens else ""
        rhs = " + ".join(self.rhs_tokens) if self.rhs_tokens else ""
        return lhs + " -> " + rhs

    def as_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "reactants": list(self.reactants),
            "products": list(self.products),
            "lhs_tokens": list(self.lhs_tokens),
            "rhs_tokens": list(self.rhs_tokens),
            "family": self.family,
            "required_projectile": self.required_projectile,
            "threshold_ev": self.threshold_ev,
            "delta_h_kj_mol": self.delta_h_kj_mol,
            "base_confidence": self.base_confidence,
            "evidence": [e.as_dict() for e in self.evidence],
            "reference_ids": list(self.reference_ids),
            "note": self.note,
            "inferred_balance": self.inferred_balance,
            "missing_products": [m.as_dict() for m in self.missing_products],
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class ReactionRecord:
    key: str
    family: str
    equation: str
    reactant_state_ids: List[str]
    product_state_ids: List[str]
    reactant_keys: List[str]
    product_keys: List[str]
    lhs_tokens: List[str]
    rhs_tokens: List[str]
    generation: int
    threshold_ev: Optional[float] = None
    delta_h_kj_mol: Optional[float] = None
    evidence: List[EvidenceRecord] = field(default_factory=list)
    confidence: Optional[ConfidenceScore] = None
    note: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def dedupe_key(self) -> str:
        return f"{self.family}|{self.equation}"

    def as_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "family": self.family,
            "equation": self.equation,
            "reactant_state_ids": list(self.reactant_state_ids),
            "product_state_ids": list(self.product_state_ids),
            "reactant_keys": list(self.reactant_keys),
            "product_keys": list(self.product_keys),
            "lhs_tokens": list(self.lhs_tokens),
            "rhs_tokens": list(self.rhs_tokens),
            "generation": self.generation,
            "threshold_ev": self.threshold_ev,
            "delta_h_kj_mol": self.delta_h_kj_mol,
            "evidence": [e.as_dict() for e in self.evidence],
            "confidence": self.confidence.as_dict() if self.confidence else None,
            "note": self.note,
            "metadata": dict(self.metadata),
            "id": self.id,
        }


@dataclass(slots=True)
class DiagnosticEntry:
    level: str
    code: str
    message: str
    context: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class BuildResult:
    species: List[SpeciesState]
    reactions: List[ReactionRecord]
    diagnostics: List[DiagnosticEntry]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "metadata": self.metadata,
            "species": [state.as_dict() for state in self.species],
            "reactions": [reaction.as_dict() for reaction in self.reactions],
            "diagnostics": [diag.as_dict() for diag in self.diagnostics],
        }

    def write_json(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.as_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
