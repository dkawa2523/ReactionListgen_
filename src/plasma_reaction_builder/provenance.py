from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


@dataclass(slots=True)
class EvidenceRecord:
    source_system: str
    source_name: str
    acquisition_method: str
    evidence_kind: str
    support_score: float
    source_url: Optional[str] = None
    locator: Optional[str] = None
    citation: Optional[str] = None
    retrieved_at: Optional[str] = None
    note: Optional[str] = None
    raw_ref: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ConfidenceScore:
    base_score: float
    evidence_bonus: float
    balance_bonus: float
    threshold_bonus: float
    thermo_bonus: float
    generation_penalty: float
    final_score: float
    tier: str

    @staticmethod
    def tier_from_score(score: float) -> str:
        if score >= 0.80:
            return "high"
        if score >= 0.55:
            return "medium"
        return "low"

    @classmethod
    def build(
        cls,
        *,
        base_score: float,
        evidence_bonus: float,
        balance_bonus: float,
        threshold_bonus: float,
        thermo_bonus: float,
        generation_penalty: float,
    ) -> "ConfidenceScore":
        final = max(0.0, min(1.0, base_score + evidence_bonus + balance_bonus + threshold_bonus + thermo_bonus - generation_penalty))
        return cls(
            base_score=base_score,
            evidence_bonus=evidence_bonus,
            balance_bonus=balance_bonus,
            threshold_bonus=threshold_bonus,
            thermo_bonus=thermo_bonus,
            generation_penalty=generation_penalty,
            final_score=final,
            tier=cls.tier_from_score(final),
        )

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)
